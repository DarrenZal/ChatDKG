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
        return '';
    }
    return url.replace(/\/$/, '');
}

function getSimpleIdentifier(url) {
    return typeof url === 'string' ? url.substring(url.lastIndexOf('/') + 1) : '';
}

function sanitizeText(text) {
    return text ? text.toString().replace(/\n/g, '\\n').replace(/\t/g, '\\t') : '';
}

function extractValue(valueObject) {
    if (typeof valueObject === 'object' && valueObject !== null) {
        return valueObject['@value'] || valueObject['@id'] || valueObject;
    }
    // Handle the case when `valueObject` is not an object or is `null`
    return '';
}

function buildEntityDetailsMap(allData) {
    console.log(`Building initial entity details map, entity count: ${allData.length}`);
    const entityDetailsMap = {};
    allData.forEach(item => {
        const entityId = item['@id'];
        const entityName = extractValue(item['http://schema.org/name']) ?? getSimpleIdentifier(entityId);
        const entityTypeArray = item['@type'];
        const entityType = entityTypeArray && entityTypeArray.length ? entityTypeArray.map(normalizeUrl) : [];
        entityDetailsMap[entityId] = { name: entityName, types: entityType };
    });
    return entityDetailsMap;
}

async function resolveLinkedEntities(entityDetailsMap, allData) {
    console.log(`Resolving linked entities with existing data, entity count: ${Object.keys(entityDetailsMap).length}`);
    allData.forEach(item => {
        // Check if 'item['http://schema.org/mentions']' exists and is an array before proceeding
        const assertions = item['http://schema.org/mentions'];
        if (Array.isArray(assertions)) {
            assertions.forEach(assertion => {
                const linkedEntityId = assertion['@id'];
                if (linkedEntityId && (!entityDetailsMap[linkedEntityId] || !entityDetailsMap[linkedEntityId].name || !entityDetailsMap[linkedEntityId].types.length)) {
                    // Extract the relevant details and build the entity details map accordingly
                    const linkedEntityName = extractValue(assertion['http://schema.org/name']) || getSimpleIdentifier(linkedEntityId);
                    const linkedEntityTypeArray = assertion['@type'];
                    const linkedEntityType = linkedEntityTypeArray && linkedEntityTypeArray.length ? linkedEntityTypeArray.map(normalizeUrl) : [];

                    entityDetailsMap[linkedEntityId] = {
                        name: linkedEntityName,
                        types: linkedEntityType,
                    };

                    console.log(`Resolved linked entity: ${linkedEntityId}, name: ${linkedEntityName}, types: ${linkedEntityType.join(', ')}`);
                }
            });
        }
    });
}

function resolveEntityValue(actualValue, entityDetailsMap) {
    if (typeof actualValue === 'string' && actualValue.startsWith('http')) {
        const entityDetails = entityDetailsMap[actualValue];
        if (entityDetails) {
            return {
                value: entityDetails.name,
                objectType: entityDetails.types.join(', ') // Join types if there are multiple
            };
        }
        // Return the simple identifier if entity cannot be resolved
        return { value: getSimpleIdentifier(actualValue), objectType: 'Linked Entity' };
    }
    return { value: actualValue, objectType: 'Literal' };
}

async function assertionsToEntityEmbeddings(assertions, ual, entityDetailsMap, attributeRecommendations, allData) {
    await resolveLinkedEntities(entityDetailsMap, allData); // Pass `allData` to the function

    const entityEmbeddings = {};

    for (const item of assertions) {
        const entityTypeUri = normalizeUrl(item['@type'] && item['@type'][0]);

        if (!entityTypeUri) {
            console.error(`Missing @type for entity: ${item['@id']}`);
            continue;
        }

        const embedding = { type: entityTypeUri, attributes: [], ual: ual };
        let foundNER = false, foundRAG = false;

        if (!attributeRecommendations[entityTypeUri]) {
            console.error(`Type not found in attribute recommendations: ${entityTypeUri}`);
            continue;
        }

        let nerValues = [];
        let ragValues = [];

        for (const predicate in item) {
            if (predicate !== '@id' && predicate !== '@type') {
                const values = Array.isArray(item[predicate]) ? item[predicate] : [item[predicate]];
                for (const valueObject of values) {
                    let resolvedData = resolveEntityValue(extractValue(valueObject), entityDetailsMap);
                    const localPredicate = getSimpleIdentifier(predicate);
                    embedding.attributes.push({ predicate: localPredicate, value: resolvedData.value, objectType: resolvedData.objectType });

                    if (attributeRecommendations[entityTypeUri]?.NER?.includes(predicate)) {
                        nerValues.push(`${localPredicate}: ${sanitizeText(resolvedData.value)}`);
                        foundNER = true;
                    }

                    if (attributeRecommendations[entityTypeUri]?.RAG?.includes(predicate) && !attributeRecommendations[entityTypeUri]?.NER?.includes(predicate)) {
                        ragValues.push(`${localPredicate}: ${sanitizeText(resolvedData.value)}`);
                        foundRAG = true;
                    }
                }
            }
        }

        if (!foundNER) {
            console.error(`Missing NER values for entity: ${item['@id']} (${entityTypeUri})`);
        }

        // Prepend the entity type to the NER values
        const entityType = getSimpleIdentifier(entityTypeUri);
        nerValues.unshift(`type: ${entityType}`);
        embedding.NER = nerValues.join('; ');
        embedding.RAG = ragValues.join('; ');
        entityEmbeddings[item['@id']] = embedding;
    }

    return entityEmbeddings;
}

function entityEmbeddingsToTsv(entityEmbeddings, attributeRecommendations) {
    console.log(`Converting entity embeddings to TSV format, entity count: ${Object.keys(entityEmbeddings).length}`);
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
        //'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181441',
        'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181442',
        'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181443',
        /* 'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181444',
        'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181445',
        'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181446',
        'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181447',
        'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/181448',
        'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1185202',
        'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181649',
        'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181509',
        'did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1181450'  */
    ]


    let allData = [];

    for (const ual of uals) {
        try {
            const jsonData = await dkg.asset.get(ual);
            if (!jsonData || !jsonData.assertion) {
                console.error(`Invalid or missing assertions in jsonData for UAL: ${ual}`);
            } else {
                allData.push(...jsonData.assertion);
                console.log(`Pushed ${jsonData.assertion.length} assertions for UAL: ${ual}`);
            }
        } catch (error) {
            console.error(`Error fetching data for UAL: ${ual}`, error);
        }
    }

    const entityDetailsMap = buildEntityDetailsMap(allData);
    await resolveLinkedEntities(entityDetailsMap, allData); // This call is okay
    let combinedEntityEmbeddings = {}; // Corrected: use `let` instead of `var`
    for (const ual of uals) {
        try {
            const jsonData = await dkg.asset.get(ual);
            if (jsonData && jsonData.assertion) {
                // Pass `allData` to the updated function call
                const embeddings = await assertionsToEntityEmbeddings(jsonData.assertion, ual, entityDetailsMap, attributeRecommendations, allData);
                combinedEntityEmbeddings = { ...combinedEntityEmbeddings, ...embeddings };
            }
        } catch (error) {
            console.error(`Error processing data for UAL: ${ual}`, error);
        }
    }

    const tsvData = entityEmbeddingsToTsv(combinedEntityEmbeddings, attributeRecommendations);
    fs.writeFileSync('entities.tsv', tsvData);
    console.log('Finished generating TSV file: entities.tsv');
})();