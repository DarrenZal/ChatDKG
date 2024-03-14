import fs from 'fs';
import 'dotenv/config';
import DKG from 'dkg.js';

const attributeRecommendations = JSON.parse(fs.readFileSync('suggestedEntityEmbeddings.json', 'utf8'));
Object.keys(attributeRecommendations).forEach(type => {
    attributeRecommendations[type].NER = attributeRecommendations[type].NER.map(attr => attr.toLowerCase());
    attributeRecommendations[type].RAG = attributeRecommendations[type].RAG.map(attr => attr.toLowerCase());
});

const dkg = new DKG({
    endpoint: 'http://194.59.205.216',
    port: 8900,
    blockchain: {
        name: 'otp::mainnet',
        publicKey: process.env.WALLET_PUBLIC_KEY_MAINNET,
        privateKey: process.env.WALLET_PRIVATE_KEY_MAINNET,
    },
});

function normalizeUrl(url) {
    if (typeof url !== 'string') {
        console.error(`URL is not a string: ${url}`);
        return '';
    }
    return url.replace(/\/$/, '');
}


function sanitizeText(text) {
    return text ? text.toString().replace(/\n/g, '\\n').replace(/\t/g, '\\t') : '';
}

function getSimpleIdentifier(entityId) {
    const parts = entityId.split(':');
    return parts[parts.length - 1];
}

function extractValue(item, entityId) {
    // Guard clause to ensure `item` is defined and prevent calling .hasOwnProperty on `undefined`.
    if (item == null) {
        return undefined;
    }
    return item.hasOwnProperty('@value') ? item['@value'] : item;
}

function getSchemaUrl(item) {
    if (item['@type'] && typeof item['@type'][0] === 'string') {
        return item['@type'][0].substring(0, item['@type'][0].lastIndexOf('/') + 1);
    } else {
        console.error(`Could not determine SCHEMA_URL for item: ${JSON.stringify(item)}`);
        return '';
    }
}

function resolveEntityValue(valueObject, entityDetailsMap, isUriPredicate = false, entityId, allData) {
    if (valueObject['@id']) {
        const resolvedId = valueObject['@id'];

        // Handle blank node identifiers
        if (resolvedId.startsWith('_:')) {
            const resolvedEntity = allData.find(item => item['@id'] === resolvedId);
            if (resolvedEntity) {
                // Process the resolved entity and add to entityDetailsMap if not already there
                extractAndStoreLinkedEntity(resolvedEntity, entityDetailsMap);
            }
        }

        return entityDetailsMap[resolvedId]?.name || getSimpleIdentifier(resolvedId);
    }
    return valueObject['@value'] || '';
}

function buildEntityDetailsMap(inputArray) {
    const entityDetailsMap = {};
    console.log(`Building entity details map with ${inputArray.length} items`);

    inputArray.forEach(item => {
        const entityId = item['@id'];
        if (!entityId) return;

        let entityDetails = {
            name: getSimpleIdentifier(entityId),
            types: item['@type'] || [],
            sourceUAL: ''  // Initialize sourceUAL as empty
        };

        const entityType = entityId.split(':')[2];
        const preferredUAL = preferredUALs[entityType];

        if (preferredUAL && (!entityDetailsMap[entityId] || entityDetailsMap[entityId].sourceUAL === '')) {
            entityDetails.sourceUAL = preferredUAL;
        }

        // Iterate over all properties
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

        entityDetailsMap[entityId] = entityDetails;
    });

    console.log(`Entity details map built with ${Object.keys(entityDetailsMap).length} entities`);
    return entityDetailsMap;
}

const preferredUALs = {
    'profile': 'did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/4162148',
    'organization': 'did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/4162411',
    'impactArea': 'did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/4162524',
    'blockchainEcosystem': 'did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/4163172',
    'foundersCircle': 'did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/4163453'/* ,
    'localNode': 'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181446',
    'deal': 'did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/4141247',
    'WorkingGroup': 'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1967103',
    'event': 'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181649',
    'content': 'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181509' */
};


function shouldUseEntityData(entityId, currentUAL, entityDetailsMap, allData) {
    const entityType = entityId.split(':')[2];
    const preferredUAL = preferredUALs[entityType];

    // Check if the entity exists in the preferred UAL dataset
    const existsInPreferredUAL = allData.some(item =>
        item['@id'] === entityId && item.ual === preferredUAL);

    const useData = currentUAL === preferredUAL || !existsInPreferredUAL;

    return useData;
}


function extractAndStoreLinkedEntity(object, entityDetailsMap) {
    const linkedEntityId = object['@id'];
    if (!linkedEntityId) return;

    // Initialize the name
    let name = linkedEntityId.startsWith('_:') ? '' : getSimpleIdentifier(linkedEntityId);

    // Check if the object has a 'name' property and extract it
    if (object.hasOwnProperty('http://schema.org/name')) {
        const nameProperty = object['http://schema.org/name'];
        if (Array.isArray(nameProperty) && nameProperty.length > 0 && nameProperty[0]['@value']) {
            name = nameProperty[0]['@value'];
        }
    }

    // Update the map with the resolved name
    entityDetailsMap[linkedEntityId] = { name: name, types: object['@type'] || [] };
}



function iterateOverProperties(object, entityDetailsMap, allData, depth = 0, parentIds = []) {
    const maxDepthBeforeLogging = 15; // Start logging when this depth is reached to avoid excessive logs

    if (depth > maxDepthBeforeLogging) {
        // Log only when approaching the max depth to reduce log volume
        console.log(`Approaching max depth at ${depth}, Current ID: ${object['@id'] || 'N/A'}, Parent Chain: ${parentIds.join(' -> ')}`);
    }

    if (depth > 20) { // Assume 20 is near the call stack limit for your environment
        console.log(`Max depth exceeded at ${depth}, Current ID: ${object['@id'] || 'N/A'}, Parent Chain: ${parentIds.join(' -> ')}`);
        throw new Error(`Recursion depth exceeded with object ID: ${object['@id'] || 'N/A'}`);
    }

    for (const property in object) {
        if (object.hasOwnProperty(property) && object[property] !== null && typeof object[property] === 'object') {
            const nextParentIds = [...parentIds, object['@id']]; // Add current object ID to the parent chain

            if (Array.isArray(object[property])) {
                object[property].forEach(subObject => {
                    iterateOverProperties(subObject, entityDetailsMap, allData, depth + 1, nextParentIds);
                });
            } else {
                iterateOverProperties(object[property], entityDetailsMap, allData, depth + 1, nextParentIds);
            }
        }
    }
}



function resolveLinkedEntities(entityDetailsMap, allData) {
    console.log(`Resolving linked entities for ${allData.length} data items`);
    allData.forEach(item => {
        iterateOverProperties(item, entityDetailsMap, allData); // Pass allData as the third argument
    });
    console.log(`Resolved linked entities`);
}


function getPredicateName(predicateUri) {
    return predicateUri.substring(predicateUri.lastIndexOf('/') + 1);
}

async function assertionsToEntityEmbeddings(assertions, ual, entityDetailsMap, attributeRecommendations, allData) {
    console.log(`Processing ${assertions.length} assertions for UAL: ${ual}`);
    const entityEmbeddings = {};

    for (const item of assertions) {
        const entityUri = normalizeUrl(item['@id']);

        if (!entityDetailsMap[entityUri] || !shouldUseEntityData(entityUri, ual, entityDetailsMap, allData)) {
            continue;
        }

        const entityTypeArray = item['@type'];
        const entityTypeUri = entityTypeArray && entityTypeArray.length > 0 ? entityTypeArray[0] : undefined;
        const entityTypeValue = entityTypeUri ? getPredicateName(entityTypeUri) : undefined;

        if (!entityTypeUri || !entityTypeValue || !attributeRecommendations[entityTypeUri]) {
            continue;
        }

        const recommendations = attributeRecommendations[entityTypeUri];
        const embedding = {
            attributes: {
                NER: [],  // Removed the type from NER
                RAG: [`type: ${entityTypeValue}`]  // Retain type in RAG
            },
            ual: ual
        };

        // Process NER fields
        recommendations.NER.forEach(predicateUri => {
            if (item.hasOwnProperty(predicateUri)) {
                const valueObject = item[predicateUri][0];
                const attributeValue = resolveEntityValue(valueObject, entityDetailsMap, false, entityUri, allData);
                // Removed the predicate name prefix for NER values
                const sanitizedValue = sanitizeText(attributeValue);
                embedding.attributes.NER.push(sanitizedValue);
            }
        });

        // Initialize RAG with NER values and additional type
        embedding.attributes.RAG = [`type: ${entityTypeValue}`, ...embedding.attributes.NER];

        // Add additional RAG fields
        recommendations.RAG.forEach(predicateUri => {
            if (item.hasOwnProperty(predicateUri) && !embedding.attributes.NER.some(attr => attr.startsWith(getPredicateName(predicateUri) + ':'))) {
                const valueObject = item[predicateUri][0];
                const attributeValue = resolveEntityValue(valueObject, entityDetailsMap, true, entityUri, allData);
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


function entityEmbeddingsToTsv(entityEmbeddings) {
    const header = 'EntityID\tNER\tRAG\tUAL';
    const rows = Object.entries(entityEmbeddings).map(([entityId, { type, NER, RAG, ual }]) => {
        // Check if entityId starts with 'http'
        if (!entityId.startsWith('http')) {
            return null; // Skip this entry
        }

        // Use placeholders for empty values if needed
        const nerValues = NER || 'N/A';
        const ragValues = RAG || 'N/A';

        return `${entityId}\t${nerValues}\t${ragValues}\t${ual || 'N/A'}`;
    });

    return [header, ...rows.filter(row => row)].join('\n');
}

(async () => {

    const uals = [
        'did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/4162148', //https://example.com/urn:profile
        'did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/4162411', //https://example.com/urn:organization
        'did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/4162524', //https://example.com/urn:impactArea
        'did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/4163172', //https://examplecom/urn:blockchainEcosystem
        'did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/4163453', //https://example.com/urn:foundersCircle
        'did:dkg:otp/0x5cac41237127f94c2d21dae0b14bfefa99880630/4141247', //https://examplecom/urn:deal

        //   'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181446', //https://example.com/urn:localNode
        //  'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1967103',  //https://examplecom/urn:WorkingGroup
        //   'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181649', //https://examplecom/urn:event 
        // 'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181509'   //https://example.com/urn:content
        // 'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181450'  //countries */
    ]
    let allData = [];

    // Fetch and combine data from each UAL
    for (const ual of uals) {
        try {
            const jsonData = await dkg.asset.get(ual);
            if (jsonData && jsonData.assertion) {
                console.log(`Fetched ${jsonData.assertion.length} assertions from UAL: ${ual}`);
                // Add the UAL to each assertion
                const assertionsWithUAL = jsonData.assertion.map(assertion => ({ ...assertion, ual }));
                allData.push(...assertionsWithUAL);
            }
        } catch (error) {
            console.error(`Error fetching data for UAL: ${ual}`, error);
        }
    }

    // Build the entity details map with the combined data
    const entityDetailsMap = buildEntityDetailsMap(allData);
    resolveLinkedEntities(entityDetailsMap, allData);

    let combinedEntityEmbeddings = {};
    for (const ual of uals) {
        try {
            const jsonData = await dkg.asset.get(ual);
            if (jsonData && jsonData.assertion) {
                const embeddings = await assertionsToEntityEmbeddings(jsonData.assertion, ual, entityDetailsMap, attributeRecommendations, allData);
                combinedEntityEmbeddings = { ...combinedEntityEmbeddings, ...embeddings };
                console.log(`Added ${Object.keys(embeddings).length} embeddings for UAL: ${ual}`);
            }
        } catch (error) {
            console.error(`Error processing data for UAL: ${ual}`, error);
        }
    }

    console.log(`Generated combined entity embeddings, total count: ${Object.keys(combinedEntityEmbeddings).length}`);
    const tsvData = entityEmbeddingsToTsv(combinedEntityEmbeddings);
    fs.writeFileSync('entitiesMainnet.tsv', tsvData);
    console.log('Finished generating TSV file: entities.tsv');
})();