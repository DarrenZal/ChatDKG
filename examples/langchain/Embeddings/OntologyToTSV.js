import fs from 'fs';
import n3 from 'n3';

const { DataFactory } = n3;
const { namedNode } = DataFactory;
const parser = new n3.Parser();
const writer = new n3.Writer({ prefixes: { schema: 'http://schema.org/' } });

const rdfType = namedNode('http://www.w3.org/1999/02/22-rdf-syntax-ns#type');
const rdfFirst = namedNode('http://www.w3.org/1999/02/22-rdf-syntax-ns#first');
const rdfRest = namedNode('http://www.w3.org/1999/02/22-rdf-syntax-ns#rest');
const owlThing = namedNode('http://www.w3.org/2002/07/owl#Thing');
const owlObjectProperty = namedNode('http://www.w3.org/2002/07/owl#ObjectProperty');
const rdfsDomain = namedNode('http://www.w3.org/2000/01/rdf-schema#domain');
const rdfsRange = namedNode('http://www.w3.org/2000/01/rdf-schema#range');

const store = new n3.Store();

const ontologyData = fs.readFileSync('../Ontology/ontology.ttl', 'utf-8');

function getLocalName(iri) {
    return iri.split(/[#\/]/).pop();
  }


// Helper functions
function extractLocalNames(quadArray) {
  const localNames = quadArray.map((quad) => {
    const obj = quad.object.id || quad.object.value;
    return obj.substring(obj.lastIndexOf('/') + 1);
  });
  return localNames;
}

function expandOwlUnion(store, object) {
  const owlUnionOf = namedNode('http://www.w3.org/2002/07/owl#unionOf');
  let items = [];
  const unions = store.getObjects(object, owlUnionOf, null);
  if (unions.length) {
    // There is a union to resolve
    let listNode = unions[0];
    while (listNode.termType === 'BlankNode') {
      const firstItem = store.getQuads(listNode, rdfFirst, null)[0].object;
      listNode = store.getQuads(listNode, rdfRest, null)[0].object;
      if (firstItem) {
        items.push(firstItem);
      }
    }
  } else {
    // It's not a union, just return the single item
    items = [object];
  }
  return items.map(item => item.id.split('/').pop()).filter(Boolean); // Return the last segment of the URI
}

// Parsing and processing
parser.parse(ontologyData, (error, quad, prefixes) => {
  if (quad) {
    store.addQuad(quad);
  } else {
    // Once parsing is done, extract the triples
    const properties = store.getQuads(null, rdfType, owlObjectProperty);
    let outputRows = [];

    properties.forEach((propertyQuad) => {
      const property = propertyQuad.subject;
      const domains = store.getQuads(property, rdfsDomain, null);
      const ranges = store.getQuads(property, rdfsRange, null);

      domains.forEach((domainQuad) => {
        const domainTypes = expandOwlUnion(store, domainQuad.object);

        ranges.forEach((rangeQuad) => {
          // For simplicity, we're treating "owl:Thing" as a special case to have only one object
          let rangeTypes = [];
          if (rangeQuad.object.equals(owlThing)) {
            rangeTypes = ["Thing"];
          } else {
            rangeTypes = expandOwlUnion(store, rangeQuad.object);
          }

          // Generate output for each combination of domain and range
          domainTypes.forEach((domainType) => {
            rangeTypes.forEach((rangeType) => {
              const row = [
                `${prefixes.schema}${domainType}`,
                propertyQuad.subject.value,
                rangeType === "Thing" ? 'owl:Thing' : `${prefixes.schema}${rangeType}`,
                `${domainType}; ${getLocalName(propertyQuad.subject.value)}; ${rangeType}`
              ];
              outputRows.push(row.join('\t'));
            });
          });
        });
      });
    });

    // Write the rows to the TSV file
    const header = 'SubjectID\tPredicate\tObjectID\tCombinedString\n';
    fs.writeFileSync('relations.tsv', header + outputRows.join('\n'));
    console.log('TSV file created successfully.');
  }
});