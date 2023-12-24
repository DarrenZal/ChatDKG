import fs from 'fs';
import 'dotenv/config';
import DKG from 'dkg.js';


const attributeRecommendations = JSON.parse(fs.readFileSync('suggestedEntityEmbeddings.json', 'utf8'));

const dkg = new DKG({
    endpoint: 'http://152.89.107.95',
    port: 8900,
    blockchain: {
        name: 'otp::testnet',
        publicKey: process.env.WALLET_PUBLIC_KEY,
        privateKey: process.env.WALLET_PRIVATE_KEY,
    },
});

function normalizeUrl(url) {
  if (typeof url !== 'string') {
    console.error(`URL is not a string: ${url}`);
    return ''; // Return an empty string or handle it in a way that suits your application
  }
  return url.replace(/\/$/, ''); // Remove trailing slash
}

function getSimpleIdentifier(url) {
  return typeof url === 'string' ? url.substring(url.lastIndexOf('/') + 1) : '';
}

function extractValue(valueObject) {
    return valueObject['@value'] || valueObject['@id'] || valueObject;
}

function sanitizeText(text) {
    return text ? text.toString().replace(/\n/g, '\\n').replace(/\t/g, '\\t') : '';
}

function buildEntityDetailsMap(allData) {
  const entityDetailsMap = {};
  allData.forEach(item => {
      const entityId = item['@id'];
      const entityTypeArray = item['@type'];
      const entityTypeValue = entityTypeArray && entityTypeArray.length ? entityTypeArray[0] : '';
      const entityTypeUri = normalizeUrl(entityTypeValue); // Use normalizeUrl safely

      if (!entityTypeUri) {
        console.error(`Missing or invalid @type for entity: ${item['@id']}`);
        return; // Skip the rest of this iteration
      }
      // Assuming the first type is the primary one
      const entityType = normalizeUrl(getSimpleIdentifier(entityTypeUri));
      entityDetailsMap[entityId] = { name: entityId, type: entityType };
  });
  return entityDetailsMap;
}

async function assertionsToEntityEmbeddings(assertions, ual, entityDetailsMap, attributeRecommendations) {
  const entityEmbeddings = {};

  for (const item of assertions) {
      // Directly extract the full URI of the entity type
      const entityTypeUri = normalizeUrl(item['@type'] && item['@type'][0]);

      if (!entityTypeUri) {
          console.error(`Missing @type for entity: ${item['@id']}`);
          continue;
      }

      const embedding = { type: entityTypeUri, attributes: [], ual: ual };
      let foundNER = false, foundRAG = false;

      // Now verify that the entity type URI is present in the attribute recommendations.
      if (!attributeRecommendations[entityTypeUri]) {
        console.error(`Type not found in attribute recommendations: ${entityTypeUri}`);
        continue;
      }

      // Use extracted entityTypeUri instead of entityTypeKey in the below logic
      for (const predicate in item) {
          if (predicate !== '@id' && predicate !== '@type') {
              const values = Array.isArray(item[predicate]) ? item[predicate] : [item[predicate]];
              for (const valueObject of values) {
                  let actualValue = extractValue(valueObject);
                  let objectType = 'Literal';

                  if (typeof actualValue === 'string' && actualValue.startsWith('http')) {
                      const entityDetails = entityDetailsMap[actualValue] || { name: actualValue, type: 'URL' };
                      actualValue = entityDetails.name;
                      objectType = entityDetails.type;
                  }

                  const localPredicate = getSimpleIdentifier(predicate);
                  embedding.attributes.push({ predicate: localPredicate, value: actualValue, objectType: objectType });

                  if (attributeRecommendations[entityTypeUri]?.NER?.includes(predicate)) {
                      foundNER = true;
                  }
                  if (attributeRecommendations[entityTypeUri]?.RAG?.includes(predicate) && !attributeRecommendations[entityTypeUri]?.NER?.includes(predicate)) {
                      foundRAG = true;
                  }
              }
          }
      }

      if (!foundNER) {
          console.error(`Missing NER values for entity: ${item['@id']} (${entityTypeUri})`);
      }

      entityEmbeddings[item['@id']] = embedding;
  }

  return entityEmbeddings;
}

function entityEmbeddingsToTsv(entityEmbeddings, attributeRecommendations) {
    const header = 'EntityID\tNER\tRAG\tUAL';
    const rows = Object.entries(entityEmbeddings).map(([entityId, { type, attributes, ual }]) => {
        const placeholder = ''; // Define a placeholder for empty values
        
        if (!entityId || !type || !attributes) {
            console.error('Missing required entity information:', entityId, type, attributes);
            return ''; // Skip this entry
        }
  
        const nerAttributes = (attributeRecommendations[type]?.NER || []).map(attr => getSimpleIdentifier(attr));
        const ragAttributes = (attributeRecommendations[type]?.RAG || []).map(attr => getSimpleIdentifier(attr));

        let nerValues = nerAttributes
            .map(attr => {
                const foundAttr = attributes.find(attribute => getSimpleIdentifier(attribute.predicate) === attr);
                return foundAttr ? `${attr}: ${sanitizeText(foundAttr.value)}` : '';
            })
            .filter(attrString => attrString !== '')
            .join('; ');

        let ragValues = ragAttributes
            .map(attr => {
                const foundAttr = attributes.find(attribute => getSimpleIdentifier(attribute.predicate) === attr && !nerAttributes.includes(attr));
                return foundAttr ? `${attr}: ${sanitizeText(foundAttr.value)}` : '';
            })
            .filter(attrString => attrString !== '')
            .join('; ');

        // Use placeholder if nerValues or ragValues are empty
        nerValues = nerValues === '' ? placeholder : nerValues;
        ragValues = ragValues === '' ? placeholder : ragValues;

        return `${entityId}\t${nerValues}\t${ragValues}\t${ual || 'N/A'}`;
    });
  
    return [header, ...rows.filter(row => row)].join('\n');
}


(async () => {
    const uals = [
    'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181441',
    'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181442',
    'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181443',
    'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181444',
    'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181445',
    'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181446',
    'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181447',
    'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/181448',
    'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1185202',
    'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181649',
    'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181509',
    'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181450']

    
    let allData = [];

    for (const ual of uals) {
        try {
            const jsonData = await dkg.asset.get(ual);
            if (!jsonData || !jsonData.assertion) {
                throw new Error(`Invalid or missing assertions in jsonData for UAL: ${ual}`);
            }
            allData.push(...jsonData.assertion);
        } catch (error) {
            console.error(`Error processing data for UAL: ${ual}`, error);
        }
    }

    const entityDetailsMap = buildEntityDetailsMap(allData);
    let combinedEntityEmbeddings = {};

    for (const ual of uals) {
      try {
          const jsonData = await dkg.asset.get(ual);
          if (jsonData && jsonData.assertion) {
              const embeddings = await assertionsToEntityEmbeddings(jsonData.assertion, ual, entityDetailsMap, attributeRecommendations);
              combinedEntityEmbeddings = { ...combinedEntityEmbeddings, ...embeddings };
          }
      } catch (error) {
          console.error(`Error processing data for UAL: ${ual}`, error);
      }
  }

    const tsvData = entityEmbeddingsToTsv(combinedEntityEmbeddings, attributeRecommendations);
    fs.writeFileSync('entities.tsv', tsvData);
})();