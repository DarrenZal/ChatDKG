// This is a simple example of creating a Knowledge Asset from a JSON file on OriginTrail DKG

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

/* (async () => {
  const result = await dkg.graph.query(
   `PREFIX schema: <https://schema.org/>

   SELECT ?s ?attribute ?value
   WHERE {
       ?s a schema:Person .
       ?s schema:url <uri:profile:TomerBariach> .
       ?s ?attribute ?value .
   }`,
   'SELECT',
   );

   console.log(result);
})(); 
*/



/* 
(async () => {
  const result = await dkg.graph.query(
   `
   PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?company ?companyName
WHERE {
  # Find the investor(s) of BioGenX
  ?bioGenX schema:investor ?investor .
  FILTER(?bioGenX = <http://example.org/companies/BioGenX>)

  # Find other companies that share the same investor
  ?company schema:investor ?investor ;
            schema:name ?companyName ;
            schema:industry ?industry .

  # Filter for companies in the renewable energy industry
  FILTER(?industry = "renewable energy")

  # Exclude BioGenX from the results
  FILTER(?company != <http://example.org/companies/BioGenX>)
}
   `,
   'SELECT',
   );

 console.log("works query: ", JSON.stringify(result, null, 2));

})();
*/

 (async () => {
  

 const result3 = await dkg.graph.query(
  `
  PREFIX schema: <http://schema.org/>

SELECT ?property ?value
WHERE {
  <http://example.org/companies/GreenyInnovation> ?property ?value.
}
  `,
  'SELECT',
  );

console.log("query 3: ", JSON.stringify(result3, null, 2));
})(); 
 



 // Function to get the asset and write to a file
async function getAssetAndWriteToFile(UAL) {
  try {
    const getAssetResult = await dkg.asset.get(UAL);
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

// Yewmakerol
//getAssetAndWriteToFile("did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/937496");

//getAssetAndWriteToFile("did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/978463"); //investor
//getAssetAndWriteToFile("did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/978599"); //private??
//getAssetAndWriteToFile("did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/978683"); //company
//getAssetAndWriteToFile("did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/978802"); //other companies

//getAssetAndWriteToFile("did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/945055"); //person
//getAssetAndWriteToFile("did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1063694"); //orgs
//getAssetAndWriteToFile("did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1078529");
//getAssetAndWriteToFile("did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1078664");
//getAssetAndWriteToFile("did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1078855");
//etAssetAndWriteToFile("did:dkg:otp/0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f/1185202");




