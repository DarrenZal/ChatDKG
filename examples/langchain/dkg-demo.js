import "dotenv/config";
import DKG from "dkg.js";
import fs from "fs";

// Parse the JSON data from file
const jsonData = JSON.parse(fs.readFileSync("../utils/data2.json"));

// Initialize the DKG client on OriginTrail DKG Testnet
const dkg = new DKG({
  endpoint: process.env.OT_NODE_HOSTNAME,
  blockchain: {
    name: "otp::testnet",
    publicKey: process.env.WALLET_PUBLIC_KEY,
    privateKey: process.env.WALLET_PRIVATE_KEY,
  },
});

// Function to create a Knowledge Asset on OriginTrail DKG
async function createKnowledgeAsset(data) {
  try {
    await dkg.asset.increaseAllowance('2069429592284014000');
   // const creationResult = await dkg.asset.burn();
    const creationResult = await dkg.asset.create(data, { epochsNum: 1 });
    console.log(`Knowledge asset UAL: ${creationResult.UAL}`);
  } catch (error) {
    console.error("Error creating Knowledge Asset:", error);
  }
}

// Main function to iterate over sections and create assets
(async () => {
  for (const section in jsonData) {
    if (section == "blockchain_ecosystems_json_ld") {
     console.log(section);
     console.log(`Creating Knowledge Asset for section: ${section}`);
     await createKnowledgeAsset(jsonData[section]);
  }
  }
})();
