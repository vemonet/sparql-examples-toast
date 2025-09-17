#!/usr/bin/env python3
import os
import re

# TODO: auto extract some stuff by parsing the SPARQL query (SELECT/CONSTRUCT, federated services)

def extract_section(text: str, section_name: str, next_section=None) -> str:
    """Extract content between two sections"""
    pattern = f"### {section_name}"
    if next_section:
        next_pattern = f"### {next_section}"
        match = re.search(f"{pattern}(.*?){next_pattern}", text, re.DOTALL)
    else:
        match = re.search(f"{pattern}(.*?)(?=### |$)", text, re.DOTALL)

    if match:
        content = match.group(1).strip()
        # Remove empty lines
        lines = [line for line in content.split('\n') if line.strip()]
        return '\n'.join(lines)
    return ""

def extract_selected_endpoint(text: str) -> str:
    """Extract the selected SPARQL endpoint"""
    endpoint_section = extract_section(text, "Select the target SPARQL endpoint")

    if "- [x] Wikidata" in endpoint_section:
        return "https://query.wikidata.org/sparql"
    elif "- [x] Wikimedia Commons" in endpoint_section:
        return "https://commons-query.wikimedia.org/sparql"
    elif "- [x] DBpedia" in endpoint_section:
        return "https://dbpedia.org/sparql"
    elif "- [x] UniProt" in endpoint_section:
        return "https://sparql.uniprot.org/sparql/"
    elif "- [x] Wikipathways" in endpoint_section:
        return "https://sparql.wikipathways.org/"
    elif "- [x] Other" in endpoint_section:
        custom_endpoint = extract_section(text, "Custom SPARQL Endpoint")
        if custom_endpoint:
            return custom_endpoint

    return "https://sparql.uniprot.org/sparql/"

def get_endpoint_namespace(target_dir: str) -> str:
    """Get the appropriate prefix by reading from the first .ttl file in the target folder"""
    import glob

    print(f"Target directory: {target_dir}")
    # if target_dir.startswith("examples/"):
    # Find the first .ttl file that is not prefixes.ttl
    pattern = os.path.join(target_dir, "*.ttl")
    ttl_files = glob.glob(pattern)

    print(f"Found .ttl files: {ttl_files}")

    for ttl_file in sorted(ttl_files):
        if not ttl_file.endswith("prefixes.ttl"):
            try:
                with open(ttl_file, 'r') as f:
                    first_line = f.readline().strip()
                    # Extract namespace from @prefix ex: <namespace> .
                    if first_line.startswith("@prefix ex:"):
                        start = first_line.find('<') + 1
                        end = first_line.find('>', start)
                        if start > 0 and end > start:
                            return first_line[start:end]
            except (IOError, IndexError):
                continue

    # Fallback to default
    return "https://example.org/.well-known/sparql-examples/"

# Read issue body from environment
issue_body = os.environ.get('GITHUB_ISSUE_BODY', '')

# Extract information
sparql_query = extract_section(issue_body, "SPARQL query")
description = extract_section(issue_body, "Query description")
filepath = extract_section(issue_body, "Query file path")
selected_endpoint = extract_selected_endpoint(issue_body)
federated_services_str = extract_section(issue_body, "Federated Service IRIs")

# Set defaults
if not filepath:
    filepath = "tmp/query.ttl"

target_dir = os.path.dirname(f"examples/{filepath}")
query_id = os.path.splitext(os.path.basename(filepath))[0]
endpoint_prefix = get_endpoint_namespace(target_dir)

# Create tmp directory
os.makedirs("examples/tmp", exist_ok=True)
if os.path.exists(f"{target_dir}/prefixes.ttl"):
    import shutil
    shutil.copy(f"{target_dir}/prefixes.ttl", "examples/tmp/prefixes.ttl")

turtle_file = f"examples/tmp/{query_id}.ttl"

# Generate turtle content
turtle_content = f"""@prefix ex: <{endpoint_prefix}> .
@prefix rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <https://schema.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix spex: <https://purl.expasy.org/sparql-examples/ontology#> .

ex:{query_id} a sh:SPARQLExecutable,
        sh:SPARQLSelectExecutable ;
    rdfs:comment "{description}"^^rdf:HTML ;
    sh:prefixes _:sparql_examples_prefixes ;
    sh:select \"\"\"{sparql_query}\"\"\" ;
    schema:target <{selected_endpoint}> """

# Add federated services if present
if "_No response_" in federated_services_str:
    turtle_content += " ."
else:
    turtle_content += f" ;\n    spex:federatesWith <{'> <'.join(federated_services_str.split('\n'))}> ."

# Write turtle file
with open(turtle_file, 'w') as f:
    f.write(turtle_content)

print(f"Created turtle file: {turtle_file}")
print(f"Target filepath: {filepath}")

# Output for GitHub Actions
with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
    f.write(f"turtle_file={turtle_file}\n")
    f.write(f"target_filepath={filepath}\n")

# Show generated content for debugging
print("Generated turtle content:")
print(turtle_content)