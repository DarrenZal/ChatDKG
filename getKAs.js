// This is a simple example of getting a Knowledge Asset and writing to a JSON file from the OriginTrail DKG

import 'dotenv/config';
import DKG from 'dkg.js';
import fs from 'fs';
import { writeFile } from 'fs/promises';


// initialize the DKG client on OriginTrail DKG Testnet
const dkg = new DKG({
  endpoint: process.env.OT_NODE_HOSTNAME,
  port: 8900,
  blockchain: {
    name: "otp::testnet",
    publicKey: process.env.WALLET_PUBLIC_KEY,
    privateKey: process.env.WALLET_PRIVATE_KEY,
  },
});

 // Function to get the asset and write to a file
async function getAssetAndWriteToFile(UAL) {
  try {
    const options = {
      state: "LATEST"
    };
    const getAssetResult = await dkg.asset.get(UAL, options);
    const resultString = JSON.stringify(getAssetResult, null, 2);

    // Define the filename
    const sanitizedUAL = UAL.replace(/[:/]/g, '_'); // Replace ':' and '/' with '_'
    const filename = sanitizedUAL + '.json';

    await writeFile(filename, resultString);

    console.log(`Results written to ${filename}`);
  } catch (error) {
    console.error("Error getting asset or writing to file:", error);
  }
} 


getAssetAndWriteToFile("did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/2679640"); //replace the KA UAL with your own





