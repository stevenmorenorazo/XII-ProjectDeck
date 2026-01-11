#!/usr/bin/env python3
"""Fix Delta Dental JSON file by replacing NaN with null and cleaning addresses."""

import json
import re

# Read the file as text first to handle NaN
with open('ucship_delta_dental_providers_2026-01-10.json', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace NaN with null (valid JSON)
content = re.sub(r'\bNaN\b', 'null', content)

# Parse the JSON
data = json.loads(content)

# Clean up addresses - remove \r\n and normalize
for provider in data['providers']:
    if provider.get('address') and isinstance(provider['address'], str):
        # Replace \r\n with space and clean up
        provider['address'] = provider['address'].replace('\r\n', ' ').replace('\n', ' ').strip()
        # Normalize multiple spaces
        provider['address'] = re.sub(r'\s+', ' ', provider['address'])

# Write back the cleaned JSON
with open('ucship_delta_dental_providers_2026-01-10.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Fixed JSON file:")
print(f"  - Replaced NaN with null")
print(f"  - Cleaned up addresses (removed \\r\\n)")
print(f"  - Total providers: {len(data['providers'])}")
print(f"  - Providers with valid addresses: {sum(1 for p in data['providers'] if p.get('address') and p['address'] != 'null')}")
