import "dotenv/config";
import DKG from "dkg.js";
import fs from "fs";

// Parse the JSON data from file
const jsonData = JSON.parse(fs.readFileSync("../utils/investor_data.json"));

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
    await dkg.asset.increaseAllowance('1969429592284014000');
    const creationResult = await dkg.asset.create(data, { epochsNum: 3 });
    console.log(`Knowledge asset UAL: ${creationResult.UAL}`);
  } catch (error) {
    console.error("Error creating Knowledge Asset:", error);
  }
}

// Main function to iterate over sections and create assets
(async () => {
  for (const section in jsonData) {
    console.log(`Creating Knowledge Asset for section: ${section}`);
    await createKnowledgeAsset(jsonData[section]);
  }
})();
