#!/usr/bin/env python3
"""Extract and group Delta Dental providers by address for HTML embedding."""

import json
import re
from collections import defaultdict

def normalize_address(address):
    """Normalize address string for comparison."""
    if not address or address == 'null':
        return ''
    return re.sub(r'\s+', ' ', str(address).strip().lower())

def get_base_address(address_str):
    """Get base address without suite/unit numbers."""
    if not address_str or address_str == 'null':
        return ''
    base = re.sub(r'\s*(ste|suite|unit|apt|apartment)\s*\.?\s*[a-z0-9]+.*$', '', address_str, flags=re.IGNORECASE)
    return base.strip().lower() if base else ''

def create_location_key(provider, use_base_address=False):
    """Create a unique key for grouping providers by location."""
    if use_base_address:
        address = get_base_address(provider.get('address') or '')
    else:
        address = normalize_address(provider.get('address') or '')
    
    city = (provider.get('city') or '').lower().strip()
    state = (provider.get('state') or '').lower().strip()
    zip_code = (provider.get('zip') or '').strip()
    
    # Create a composite key
    key = f"{address}|{city}|{state}|{zip_code}"
    return key

def get_full_address(provider):
    """Get the full formatted address string from a provider."""
    parts = []
    if provider.get('address') and provider.get('address') != 'null':
        parts.append(str(provider['address']))
    if provider.get('city') and provider.get('city') != 'null':
        parts.append(str(provider['city']))
    if provider.get('state') and provider.get('state') != 'null':
        parts.append(str(provider['state']))
    if provider.get('zip') and provider.get('zip') != 'null':
        parts.append(str(provider['zip']))
    
    return ', '.join(parts) if parts else None

# Load the Delta Dental data
with open('ucship_delta_dental_providers_2026-01-10.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Group providers by address (using base address to group by building)
grouped = defaultdict(list)
for provider in data['providers']:
    # Skip providers without valid addresses
    if not provider.get('address') or provider.get('address') == 'null':
        continue
    
    key = create_location_key(provider, use_base_address=True)
    grouped[key].append(provider)

# Build locations array
locations = []
for key, providers in grouped.items():
    if not providers:
        continue
    
    # Use the first provider's address info for the location
    first_provider = providers[0]
    full_address = get_full_address(first_provider)
    
    if not full_address:
        continue
    
    # Extract location info
    location = {
        'address': first_provider.get('address') or '',
        'city': first_provider.get('city') or '',
        'state': first_provider.get('state') or '',
        'zip': first_provider.get('zip') or '',
        'full_address': full_address,
        'phone': first_provider.get('phone') or None,
        'county': None  # Delta Dental data doesn't have county
    }
    
    # Clean up phone - remove null
    if location['phone'] == 'null':
        location['phone'] = None
    
    # Format providers for display
    formatted_providers = []
    for p in providers:
        formatted_provider = {
            'name': p.get('name') or 'Dental Provider',
            'specialty': p.get('specialty') or 'Dental',
            'phone': p.get('phone') or None,
            'website': p.get('website') or None
        }
        # Clean up null values
        if formatted_provider['phone'] == 'null':
            formatted_provider['phone'] = None
        if formatted_provider['website'] == 'null':
            formatted_provider['website'] = None
        formatted_providers.append(formatted_provider)
    
    locations.append({
        'location': location,
        'provider_count': len(formatted_providers),
        'providers': formatted_providers
    })

# Output as JavaScript variable
js_output = 'const locationsData = ' + json.dumps(locations, indent=2, ensure_ascii=False) + ';'
print(js_output)
