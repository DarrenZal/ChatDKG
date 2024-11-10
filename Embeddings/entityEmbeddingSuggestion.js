import OpenAI from "openai";
import 'dotenv/config';
import fs from 'fs';

// Function to parse ontology file and build a prefix-URI mapping
function extractPrefixMapping(ontology) {
    const lines = ontology.split('\n');
    const prefixMapping = {};
    for (const line of lines) {
        if (line.startsWith('@prefix')) {
            const parts = line.match(/^@prefix (\w+): <(.+)> \.$/);
            if (parts) {
                const [ , prefix, uri ] = parts;
                prefixMapping[prefix + ':'] = uri;
            }
        }
    }
    return prefixMapping;
}

// Function to replace prefixes with full URIs in GPT-4's recommendations
function applyFullUrisToRecommendations(recommendations, prefixMapping) {
    const updatedRecommendations = {};
    for (const key in recommendations) {
        const newKey = key.replace(/(\w+):/, match => prefixMapping[match] || match);
        updatedRecommendations[newKey] = {};
        for (const attrType in recommendations[key]) {
            updatedRecommendations[newKey][attrType] = recommendations[key][attrType].map(attr =>
                attr.replace(/(\w+):/, match => prefixMapping[match] || match)
            );
        }
    }
    return updatedRecommendations;
}

async function analyzeOntologyWithGPT4(ontology) {
    const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
    const prefixMapping = extractPrefixMapping(ontology);

    try {
        const chatCompletion = await openai.chat.completions.create({
            messages: [{
                role: "user", 
                content: `Analyze the following ontology and suggest attributes to embed for each entity type. The attributes will be used for two purposes: named entity recognition (NER) and Retrieval-Augmented Generation (RAG) in a natural language chatbot. For NER, suggest attributes (at least one) that will be effective for entity linking. For RAG, suggest additional attributes that provide richer context for generating responses but are not already covered by the NER attributes. Both 'NER' and 'RAG' attributes will be used for RAG, so no duplication is necessary. Present the results in JSON format:\n\n${ontology}`
            }],
            response_format: { "type": "json_object" },
            model: "gpt-4-1106-preview",
        });

        const extracted_content = chatCompletion.choices[0].message.content;
        console.log("Response from OpenAI:", extracted_content);

        // Convert the JSON string to an object
        const recommendations = JSON.parse(extracted_content);
        console.log("Parsed Recommendations:", recommendations);

        // Check the structure before calling applyFullUrisToRecommendations
        for (const key in recommendations) {
            for (const attrType in recommendations[key]) {
                if (!Array.isArray(recommendations[key][attrType])) {
                    console.error(`TypeError: ${key}[${attrType}] is not an array.`, recommendations[key][attrType]);
                }
            }
        }
        // Apply the full URIs to the recommendations using our prefixMapping
        const updatedRecommendations = applyFullUrisToRecommendations(recommendations, prefixMapping);

        // Write the updated recommendations to a JSON file
        fs.writeFileSync('suggestedEntityEmbeddings.json', JSON.stringify(updatedRecommendations, null, 2));
        return updatedRecommendations; // Optional: Return the data for further use
    } catch (error) {
        console.error("Error in OpenAI request:", error);
        return null; // Return null or handle the error as needed
    }
}

const ontology = fs.readFileSync("../Ontology/ontology.ttl").toString();

// Run the analysis
analyzeOntologyWithGPT4(ontology)
    .then(result => {
        console.log("Analysis complete. Check the output file.");
    })
    .catch(error => {
        console.error("An error occurred:", error);
    });

export { analyzeOntologyWithGPT4 };