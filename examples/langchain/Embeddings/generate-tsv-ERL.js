import fs from 'fs';
import 'dotenv/config';
import DKG from 'dkg.js';

const dkg = new DKG({
  endpoint: 'http://152.89.107.95',
  port: 8900,
  blockchain: {
    name: 'otp::testnet',
    publicKey: process.env.WALLET_PUBLIC_KEY,
    privateKey: process.env.WALLET_PRIVATE_KEY,
  },
});

// Convert entity embeddings TSV to an object for easier combination
function entityEmbeddingsToObj(tsvString) {
  const rows = tsvString.split('\n').slice(1); // Skip header
  const obj = {};
  rows.forEach(row => {
    const [entityId, embedding, ual] = row.split('\t');
    const attributes = embedding.split('; ').map(attr => {
      const index = attr.indexOf(':');
      const predicate = attr.substring(0, index);
      const value = attr.substring(index + 1);
      return { predicate, value };
    });
    obj[entityId] = { id: entityId, attributes: attributes, ual };
  });
  return obj;
}

// Function to sanitize text to be TSV-friendly
function sanitizeText(text) {
  if (Array.isArray(text)) {
    return text.map(t => t.toString().replace(/\n/g, '\\n').replace(/\t/g, '\\t')).join(', ');
  }
  return text ? text.toString().replace(/\n/g, '\\n').replace(/\t/g, '\\t') : '';
}

// Function to convert entity embeddings to TSV format including the UAL
function entityEmbeddingsToTsv(entityEmbeddings) {
  const header = 'EntityID\tEmbedding\tUAL';
  const rows = Object.entries(entityEmbeddings).map(([entityId, { attributes, ual }]) => {
    // Sort attributes by predicate in alphabetical order
    const sortedAttributes = attributes.sort((a, b) => a.predicate.localeCompare(b.predicate));
    const embeddingStr = sortedAttributes.map(attr => `${attr.predicate}:${attr.value}`).join('; ');
    return `${entityId}\t${sanitizeText(embeddingStr)}\t${ual}`;
  });
  return [header, ...rows].join('\n');
}

const nameCache = {};

const detailsCache = {};

async function fetchEntityDetails(entityUrl) {
  console.log(entityUrl);
  if (detailsCache[entityUrl]) {
    return detailsCache[entityUrl];
  }

  const query = `
  SELECT ?name ?type
  WHERE { 
    <${entityUrl}> ?namePredicate ?name .
    <${entityUrl}> rdf:type ?type .
    FILTER (regex(str(?namePredicate), "name|label", "i")) 
  }
  `;
  const result = await dkg.graph.query(query, 'SELECT');

  if (result && result.data && result.data.length > 0) {
    const details = {
      name: result.data[0].name ? result.data[0].name.replace(/['"]+/g, '') : entityUrl,
      type: result.data[0].type ? result.data[0].type.split('/').pop() : 'URL'
    };
    console.log(details);
    detailsCache[entityUrl] = details;
    return details;
  }

  console.log(entityUrl);
  detailsCache[entityUrl] = { name: entityUrl, type: 'URL' };
  return { name: entityUrl, type: 'URL' };
}

function extractValue(value) {
  if (typeof value === 'object') {
    if (value['@id']) {
      return value['@id'];
    }
    // Return the '@value' property for simpler representations
    return value['@value'] || JSON.stringify(value);
  }
  return value;
}

// Function to extract and convert assertions to TSV format for relations and attributes
async function assertionsToTsvAndEmbeddings(assertions, ual, allData, uniqueRelations) {
  const entityEmbeddings = {};

  for (const item of assertions) {
    const entityType = String(item['@type']).split('/').pop();
    const entityId = item['@id'];

    const embeddingWithUal = {
      type: entityType,
      attributes: [],
      ual: ual,
    };

    if (!entityEmbeddings[entityId]) {
      entityEmbeddings[entityId] = embeddingWithUal;
      entityEmbeddings[entityId].attributes.push({ predicate: '@type', value: entityType });
    }

    for (const predicate of Object.keys(item)) {
      if (predicate !== '@id' && predicate !== '@type') {
        const values = Array.isArray(item[predicate]) ? item[predicate] : [item[predicate]];

        for (const value of values) {
          let actualValue = extractValue(value);

          if (typeof actualValue === 'string' && actualValue.startsWith('http://')) {
            const entityDetails = await fetchEntityDetails(actualValue);
            actualValue = entityDetails.name;
          }

          const localPredicate = predicate.split('/').pop();
          entityEmbeddings[entityId].attributes.push({ predicate: localPredicate, value: actualValue });

          // Updating how the relation key and embedding are constructed
          const fullPredicate = predicate; // Full URI predicate
          const embedding = localPredicate; // Simplified to only include the predicate name
          const relationKey = `${fullPredicate}\t${embedding}`; // Key with URI predicate and simplified embedding
          uniqueRelations.set(relationKey, embedding);
        }
      }
    }
  }

  return entityEmbeddings;
}

// The asynchronous IIFE (Immediately Invoked Function Expression)
(async () => {

  const uals = [
    "did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1165451",
    "did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1165486",
    "did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1165562",
    "did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1165625"
    // Add additional UALs here
  ];

  let combinedEntityEmbeddings = {};
  let allData = [];
  let uniqueRelations = new Map();

  for (const ual of uals) {
    try {
      const jsonData = await dkg.asset.get(ual);
      if (!jsonData || !jsonData.assertion) {
        throw new Error(`Invalid or missing assertions in jsonData for UAL: ${ual}`);
      }

      allData.push(...Object.values(jsonData.assertion));

      const entityEmbeddings = await assertionsToTsvAndEmbeddings(jsonData.assertion, ual, allData, uniqueRelations);
      combinedEntityEmbeddings = { ...combinedEntityEmbeddings, ...entityEmbeddings };
    } catch (error) {
      console.error(`Error processing data for UAL: ${ual}`, error);
    }
  }

  // Create TSV rows from the unique relations with count
  const relationHeader = 'Predicate\tEmbedding';
  const relationRows = Array.from(uniqueRelations.entries()).map(([key, embedding]) => {
    return `${key}`; // Simplified to prevent duplication
  });

  // Write the combined TSV outputs to files
  fs.writeFileSync('relations.tsv', [relationHeader, ...relationRows].join('\n'));

  // Write the combined TSV outputs to files
  fs.writeFileSync('entities.tsv', entityEmbeddingsToTsv(combinedEntityEmbeddings));


})();