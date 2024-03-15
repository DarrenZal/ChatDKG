import "dotenv/config";
import DKG from "dkg.js";
import fs from "fs";

// Parse the JSON data from file
const jsonData = JSON.parse(fs.readFileSync("../utils/data.json"));

const dkg = new DKG({
  endpoint: process.env.ENDPOINT_MAINNET,
  port: 8900,
  blockchain: {
    name: 'otp::mainnet',
    publicKey: process.env.WALLET_PUBLIC_KEY_MAINNET,
    privateKey: process.env.WALLET_PRIVATE_KEY_MAINNET,
  },
});

/* console.log("increasing allowance");
await dkg.asset.increaseAllowance('4569429592284014000');
console.log("done increasing allowance"); */

// Function to create a Knowledge Asset on OriginTrail DKG
async function createKnowledgeAsset(data) {
  try {
   // const creationResult = await dkg.asset.burn();
   const creationResult = await dkg.asset.create(data, { epochsNum: 1 });
    console.log(`Knowledge asset UAL: ${creationResult.UAL}`);
  } catch (error) {
    console.error("Error creating Knowledge Asset:", error);
  }
}


(async () => {
  for (const section in jsonData) {
     console.log(`Creating Knowledge Asset for section: ${section}`);
     await createKnowledgeAsset(jsonData[section]);
  }
})();