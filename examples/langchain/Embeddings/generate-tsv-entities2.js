import fs from 'fs';
import 'dotenv/config';
import DKG from 'dkg.js';

// Load attribute recommendations from a JSON file
const attributeRecommendations = JSON.parse(fs.readFileSync('suggestedEntityEmbeddings.json', 'utf8'));

// Initialize DKG client with endpoint and blockchain credentials
const dkg = new DKG({
    endpoint: 'http://152.89.107.95',
    port: 8900,
    blockchain: {
        name: 'otp::testnet',
        publicKey: process.env.WALLET_PUBLIC_KEY,
        privateKey: process.env.WALLET_PRIVATE_KEY,
    },
});

// Function to normalize URLs by removing trailing slashes
function normalizeUrl(url) {
    if (typeof url !== 'string') {
        console.error(`URL is not a string: ${url}`);
        return '';
    }
    return url.replace(/\/$/, '');
}

// Sanitize text by escaping newline and tab characters
function sanitizeText(text) {
    return text ? text.toString().replace(/\n/g, '\\n').replace(/\t/g, '\\t') : '';
}

// Extract the last part of an entity ID
function getSimpleIdentifier(entityId) {
    const parts = entityId.split(':');
    return parts[parts.length - 1];
}

// Extract value from an item; handles objects with '@value' key
function extractValue(item) {
    if (item == null) {
        return undefined;
    }
    return item.hasOwnProperty('@value') ? item['@value'] : item;
}

// Get schema URL from item's type
function getSchemaUrl(item) {
    if(item['@type'] && typeof item['@type'][0] === 'string') {
        return item['@type'][0].substring(0, item['@type'][0].lastIndexOf('/')+1); 
    } else {
        console.error(`Could not determine SCHEMA_URL for item: ${JSON.stringify(item)}`);
        return '';
    }
}

// Resolve the value of an entity, handling URIs and ID references
function resolveEntityValue(valueObject, entityDetailsMap, isUriPredicate = false) {
    if (typeof valueObject === 'object' && valueObject !== null) {
        if (valueObject['@id'] === "_:c14n593") {
            console.log(`entityDetailsMap for _ :c14n593:`, entityDetailsMap["_:c14n593"]);
        }
        if (valueObject['@id'] && !isUriPredicate) {
            const entityId = valueObject['@id'];
            return entityDetailsMap[entityId]?.name || getSimpleIdentifier(entityId);
        } else if (valueObject['@id'] && isUriPredicate) {
            return valueObject['@id'];
        }
    }
    return valueObject['@value'] || '';
}

// Build a map of entity details from the input array
function buildEntityDetailsMap(inputArray) {
    const entityDetailsMap = {};

    inputArray.forEach(item => {
        const entityId = item['@id'];
        if (!entityId) return;

        let entityDetails = {
            name: getSimpleIdentifier(entityId),
            types: item['@type'] || []
        };

        for (const property in item) {
            if (property !== '@id' && property !== '@type') {
                const valueArray = item[property];
                if (property.endsWith('/name')) {
                    const nameObject = valueArray.find(v => v['@value']);
                    if (nameObject) {
                        entityDetails.name = nameObject['@value'];
                    }
                } else {
                    entityDetails[property.split('/').pop()] = extractValue(valueArray[0], entityId);
                }
            }
        }

        if (entityId === "_:c14n593") {
            console.log(`Adding to entityDetailsMap: ${entityId} with details:`, entityDetails);
        }

        entityDetailsMap[entityId] = entityDetails;
    });

    return entityDetailsMap;
}

// Function to extract and store linked entity details from a given object
function extractAndStoreLinkedEntity(object, entityDetailsMap) {
    const linkedEntityId = object['@id'];
    if (linkedEntityId && (!entityDetailsMap[linkedEntityId] ||
        !entityDetailsMap[linkedEntityId].name ||
        !(entityDetailsMap[linkedEntityId].types && entityDetailsMap[linkedEntityId].types.length))) {

        const nameProperty = object['http://schema.org/name'];
        const linkedEntityName = Array.isArray(nameProperty) && nameProperty.length > 0
            ? extractValue(nameProperty[0])
            : getSimpleIdentifier(linkedEntityId);

        const linkedEntityTypeArray = object['@type'];
        const linkedEntityType = linkedEntityTypeArray && linkedEntityTypeArray.length
            ? linkedEntityTypeArray.map(normalizeUrl)
            : [];

        entityDetailsMap[linkedEntityId] = {
            name: linkedEntityName,
            types: linkedEntityType,
        };
    }
}

// Recursively iterate over properties of an object to extract and store linked entities
function iterateOverProperties(object, entityDetailsMap) {
    for (const property in object) {
        if (object[property] !== null && typeof object[property] === 'object') {
            if (Array.isArray(object[property])) {
                object[property].forEach(subObject => {
                    extractAndStoreLinkedEntity(subObject, entityDetailsMap);
                    iterateOverProperties(subObject, entityDetailsMap); // Recurse
                });
            } else {
                extractAndStoreLinkedEntity(object[property], entityDetailsMap);
                iterateOverProperties(object[property], entityDetailsMap); // Recurse
            }
        }
    }
}

// Resolve linked entities in the dataset
function resolveLinkedEntities(entityDetailsMap, allData) {
    allData.forEach(item => {
        iterateOverProperties(item, entityDetailsMap);
    });
}

// Get the predicate name from a URI
function getPredicateName(predicateUri) {
    return predicateUri.substring(predicateUri.lastIndexOf('/') + 1);
}

// Function to convert assertions to entity embeddings
async function assertionsToEntityEmbeddings(assertions, ual, entityDetailsMap, attributeRecommendations, allData) {
    await resolveLinkedEntities(entityDetailsMap, allData);

    const entityEmbeddings = {};

    for (const item of assertions) {
        const entityUri = normalizeUrl(item['@id']);
        const entityTypeArray = item['@type'];
        const entityTypeUri = entityTypeArray && entityTypeArray.length > 0 ? normalizeUrl(entityTypeArray[0]) : undefined;
        const entityTypeValue = entityTypeUri ? getPredicateName(entityTypeArray[0]) : undefined;

        if (!entityTypeUri || !entityTypeValue) {
            console.error(`Missing or invalid @type for entity: ${entityUri}`);
            continue;
        }

        const recommendations = attributeRecommendations[entityTypeUri] || { NER: [], RAG: [] };

        const embedding = {
            attributes: {
                NER: [`type: ${entityTypeValue}`], // Initialize NER with entity type
                RAG: [] // Initialize an empty array for RAG
            },
            ual: ual
        };

        recommendations.NER.forEach(predicateUri => {
            if (item.hasOwnProperty(predicateUri)) {
                const valueObject = item[predicateUri][0];
                const attributeValue = resolveEntityValue(valueObject, entityDetailsMap);
                const predicateName = getPredicateName(predicateUri);
                const sanitizedValue = sanitizeText(attributeValue);
                embedding.attributes.NER.push(`${predicateName}: ${sanitizedValue}`);
            }
        });
        embedding.attributes.RAG = Array.from(embedding.attributes.NER); // Start RAG with NER values

        recommendations.RAG.forEach(predicateUri => {
            if (item.hasOwnProperty(predicateUri) && !embedding.attributes.NER.some(attr => attr.startsWith(getPredicateName(predicateUri) + ':'))) {
                const valueObject = item[predicateUri][0];
                const attributeValue = resolveEntityValue(valueObject, entityDetailsMap, true);
                const predicateName = getPredicateName(predicateUri);
                const sanitizedValue = sanitizeText(attributeValue);
                embedding.attributes.RAG.push(`${predicateName}: ${sanitizedValue}`);
            }
        });

        embedding.NER = embedding.attributes.NER.join('; ');
        embedding.RAG = embedding.attributes.RAG.join('; ');

        entityEmbeddings[entityUri] = embedding;
    }

    return entityEmbeddings;
}

// Convert entity embeddings to TSV format, excluding non-HTTP entity IDs
function entityEmbeddingsToTsv(entityEmbeddings, attributeRecommendations) {
    const header = 'EntityID\tNER\tRAG\tUAL';
    const rows = Object.entries(entityEmbeddings).map(([entityId, { type, NER, RAG, ual }]) => {
        if (!entityId.startsWith('http')) {
            return null; // Exclude non-HTTP entity IDs
        }

        const nerValues = NER || 'N/A';
        const ragValues = RAG || 'N/A';

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
       // 'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181450'  //countries
    ]
    let allData = [];

    // Fetch data for each UAL and process it
    for (const ual of uals) {
        try {
            const jsonData = await dkg.asset.get(ual);
            if (!jsonData || !jsonData.assertion) {
                console.error(`Invalid or missing assertions in jsonData for UAL: ${ual}`);
            } else {
                allData.push(...jsonData.assertion);
            }
        } catch (error) {
            console.error(`Error fetching data for UAL: ${ual}`, error);
        }
    }

    // Create embeddings
    const entityDetailsMap = buildEntityDetailsMap(allData);
    await resolveLinkedEntities(entityDetailsMap, allData);
    let combinedEntityEmbeddings = {};
    for (const ual of uals) {
        try {
            const jsonData = await dkg.asset.get(ual);
            if (jsonData && jsonData.assertion) {
                const embeddings = await assertionsToEntityEmbeddings(jsonData.assertion, ual, entityDetailsMap, attributeRecommendations, allData);
                combinedEntityEmbeddings = { ...combinedEntityEmbeddings, ...embeddings };
            }
        } catch (error) {
            console.error(`Error processing data for UAL: ${ual}`, error);
        }
    }

    //write embedding tsv to a file
    const tsvData = entityEmbeddingsToTsv(combinedEntityEmbeddings, attributeRecommendations);
    fs.writeFileSync('entities.tsv', tsvData);
    console.log('Finished generating TSV file: entities.tsv');
})();