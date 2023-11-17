import fs from 'fs';
import 'dotenv/config';
import DKG from 'dkg.js';

// The asynchronous IIFE (Immediately Invoked Function Expression) to use async/await at the top level
(async () => {
  // Initialize the DKG client on OriginTrail DKG Testnet
  const dkg = new DKG({
    endpoint: 'http://152.89.107.95',
    port: 8900,
    blockchain: {
      name: 'otp::testnet',
      publicKey: process.env.WALLET_PUBLIC_KEY,
      privateKey: process.env.WALLET_PRIVATE_KEY,
    },
  });

  // Define the Universal Asset Locator (UAL)
  const ual = "did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/978802";
  //const ual = "did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/978683";
  //const ual = "did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/978463";

  // Fetch data from the DKG
  let jsonData;
  try {
    jsonData = await dkg.asset.get(ual);
    // Ensure jsonData has the assertions property
    if (!jsonData || !jsonData.assertion) {
      throw new Error('Invalid or missing assertions in jsonData');
    }
  } catch (error) {
    console.error('Error fetching data:', error);
    return;
  }

  // Process assertions to TSV
  try {
    const { relationTsv, entityEmbeddingsTsv } = assertionsToTsvAndEmbeddings(jsonData.assertion, ual);

    // Write the TSV outputs to files
    fs.writeFileSync('relations.tsv', relationTsv);
    fs.writeFileSync('entities.tsv', entityEmbeddingsTsv);
  } catch (error) {
    console.error('Error processing data:', error);
  }
})();

// Function to sanitize text to be TSV-friendly
function sanitizeText(text) {
  return text.replace(/\n/g, '\\n').replace(/\t/g, '\\t');
}

// Function to extract and convert assertions to TSV format for relations, and create entity embeddings
function assertionsToTsvAndEmbeddings(assertions, ual) {
  const entityEmbeddings = {};
  const relationRows = [];

  assertions.forEach((item) => {
    const entityId = item['@id'];
    const embeddingWithUal = {
      id: sanitizeText(entityId),
      attributes: [],
      ual: ual, // Using UAL here
    };

    // Initialize an embedding with the ID and UAL if it doesn't exist
    if (!entityEmbeddings[entityId]) {
      entityEmbeddings[entityId] = embeddingWithUal;
    }

    Object.keys(item).forEach((predicate) => {
      if (predicate !== '@id') {
        item[predicate].forEach((obj) => {
          const value = obj['@id'] || obj['@value'];
          const row = [sanitizeText(entityId), sanitizeText(predicate), sanitizeText(value)];

          // Check if the predicate should be treated as a relation or an attribute
          const isRelation = obj.hasOwnProperty('@id') || predicate.startsWith('http://schema.org/');

          if (isRelation && obj.hasOwnProperty('@id')) {
            // It's a relation, add it to the relationRows
            relationRows.push(row.join('\t'));
            
            // Ensure related entity is also initialized in entityEmbeddings if it's an entity
            if (!entityEmbeddings[value]) {
              entityEmbeddings[value] = { id: sanitizeText(value), attributes: [], ual: ual };
            }
          } else {
            // It's an attribute, add it to entity embeddings
            entityEmbeddings[entityId].attributes.push({
              predicate: sanitizeText(predicate),
              value: sanitizeText(value),
            });
          }
        });
      }
    });
  });
  

  // Headers for TSV files
  const relationHeader = 'SubjectID\tPredicate\tObjectID';

  // Joining relation rows with headers
  const relationTsv = [relationHeader, ...relationRows].join('\n');

  // Convert entity embeddings to TSV format
  const entityEmbeddingsTsv = entityEmbeddingsToTsv(entityEmbeddings);

  return { relationTsv, entityEmbeddingsTsv };
}

// Function to convert entity embeddings to TSV format including the UAL
function entityEmbeddingsToTsv(entityEmbeddings) {
  const header = 'EntityID\tEmbedding\tUAL';
  const rows = Object.entries(entityEmbeddings).map(([entityId, { attributes, ual }]) => {
    const embeddingStr = attributes.map((attr) => `${attr.predicate}:${attr.value}`).join('; ');
    return `${entityId}\t${sanitizeText(embeddingStr)}\t${ual}`;
  });
  return [header, ...rows].join('\n');
}
