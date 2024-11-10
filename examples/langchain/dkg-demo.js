import "dotenv/config";
import DKG from "dkg.js";
import fs from "fs";

// Parse the JSON data from file
const jsonData = JSON.parse(fs.readFileSync("../utils/data.json"));

const dkg = new DKG({
  endpoint: process.env.OT_NODE_HOSTNAME,
  blockchain: {
    name: "otp::testnet",
    publicKey: process.env.WALLET_PUBLIC_KEY,
    privateKey: process.env.WALLET_PRIVATE_KEY,
  },
});


// NOTE: You will need OTP and TRAC testnet tokens for the next operation. You can get them on the OriginTrail Discord token faucet, as explained here: 
// https://docs.origintrail.io/decentralized-knowledge-graph-layer-2/testnet-node-setup-instructions/fund-your-v6-testnet-node
(async () => {
  // creating a Knowledge Asset on OriginTrail DKG
   const creationResult = await dkg.asset.create(jsonData, { epochsNum: 1 });

   console.log(`Knowledge asset UAL: ${creationResult.UAL}`);
})();