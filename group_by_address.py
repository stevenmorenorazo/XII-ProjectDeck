#!/usr/bin/env python3
"""
Script to group JSON provider data by address location.
Groups providers that share the same address, city, state, and zip code.

Usage:
    python group_by_address.py [input_file] [output_file] [use_base_address]
    
Arguments:
    input_file: Path to input JSON file (default: ucship_anthem_providers_grouped_2026-01-10.json)
    output_file: Path to output JSON file (default: ucship_anthem_providers_by_address.json)
    use_base_address: If 'true', groups by base address without suite numbers (default: false)
    
Examples:
    # Basic usage with defaults
    python group_by_address.py
    
    # Specify custom files
    python group_by_address.py input.json output.json
    
    # Use base address grouping (consolidates suites in same building)
    python group_by_address.py input.json output.json true
"""

import json
import re
from collections import defaultdict
from typing import Dict, List, Any


def normalize_address(address: str) -> str:
    """
    Normalize address string for comparison.
    Standardizes formatting but keeps suite/unit info for better grouping.
    """
    if not address:
        return ""
    
    # Convert to string and handle None
    address_str = str(address) if address is not None else ""
    if not address_str:
        return ""
    
    # Convert to lowercase and strip whitespace
    normalized = address_str.lower().strip()
    
    # Normalize common abbreviations (but keep suite/unit info)
    # Standardize street type abbreviations
    normalized = re.sub(r'\b(st|street)\b\.?', 'street', normalized)
    normalized = re.sub(r'\b(ave|avenue)\b\.?', 'avenue', normalized)
    normalized = re.sub(r'\b(rd|road)\b\.?', 'road', normalized)
    normalized = re.sub(r'\b(blvd|boulevard)\b\.?', 'boulevard', normalized)
    normalized = re.sub(r'\b(dr|drive)\b\.?', 'drive', normalized)
    normalized = re.sub(r'\b(ct|court)\b\.?', 'court', normalized)
    normalized = re.sub(r'\b(ln|lane)\b\.?', 'lane', normalized)
    
    # Normalize suite/unit abbreviations but keep the identifier
    normalized = re.sub(r'\b(ste|suite)\s*\.?\s*', 'ste ', normalized)
    normalized = re.sub(r'\b(unit|apt|apartment)\s*\.?\s*', 'unit ', normalized)
    
    # Remove extra whitespace and punctuation inconsistencies
    normalized = re.sub(r'[,\s]+', ' ', normalized)
    normalized = normalized.strip()
    
    return normalized


def get_base_address(address: str) -> str:
    """
    Extract base address without suite/unit numbers for broader grouping.
    """
    if not address:
        return ""
    
    address_str = str(address) if address is not None else ""
    if not address_str:
        return ""
    
    # Remove suite/unit information for base address grouping
    base = re.sub(r'\s*(ste|suite|unit|apt|apartment)\s*\.?\s*[a-z0-9]+.*$', '', address_str, flags=re.IGNORECASE)
    base = base.strip()
    return base.lower() if base else ""


def create_location_key(provider: Dict[str, Any], use_base_address: bool = False) -> str:
    """
    Create a unique key for grouping providers by location.
    Uses address, city, state, and zip code.
    
    Args:
        provider: Provider dictionary
        use_base_address: If True, groups by base address (without suite numbers)
    """
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


def get_full_address(provider: Dict[str, Any]) -> str:
    """
    Get the full formatted address string from a provider.
    """
    parts = []
    if provider.get('address'):
        parts.append(str(provider['address']))
    if provider.get('city'):
        parts.append(str(provider['city']))
    if provider.get('state'):
        parts.append(str(provider['state']))
    if provider.get('zip'):
        parts.append(str(provider['zip']))
    
    return ', '.join(parts)


def group_providers_by_address(input_file: str, output_file: str = None, use_base_address: bool = False) -> Dict[str, Any]:
    """
    Read JSON file and group providers by address location.
    
    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file (optional)
    
    Returns:
        Dictionary with grouped providers
    """
    # Read input JSON
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract all providers from all categories
    all_providers = []
    for category, providers in data.get('grouped_providers', {}).items():
        for provider in providers:
            # Add category info to each provider
            provider_with_category = provider.copy()
            provider_with_category['original_category'] = category
            all_providers.append(provider_with_category)
    
    # Group providers by location
    location_groups = defaultdict(list)
    for provider in all_providers:
        location_key = create_location_key(provider, use_base_address=use_base_address)
        location_groups[location_key].append(provider)
    
    # Create output structure
    grouped_by_location = []
    for location_key, providers in sorted(location_groups.items()):
        # Get representative address info from first provider
        first_provider = providers[0]
        full_address = get_full_address(first_provider)
        
        location_entry = {
            "location": {
                "address": first_provider.get('address', ''),
                "city": first_provider.get('city', ''),
                "state": first_provider.get('state', ''),
                "zip": first_provider.get('zip', ''),
                "county": first_provider.get('county', ''),
                "full_address": full_address,
                "phone": first_provider.get('phone', ''),
                "website": first_provider.get('website'),
                "distance_miles": first_provider.get('distance_miles'),
            },
            "provider_count": len(providers),
            "providers": providers
        }
        
        grouped_by_location.append(location_entry)
    
    # Sort by address for easier reading
    grouped_by_location.sort(key=lambda x: x['location']['full_address'])
    
    # Create output structure
    output_data = {
        "meta": data.get('meta', {}).copy(),
        "meta_grouped": {
            "total_locations": len(grouped_by_location),
            "total_providers": len(all_providers),
            "grouping_method": "by_base_address" if use_base_address else "by_address_location"
        },
        "locations": grouped_by_location
    }
    
    # Write output file if specified
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"[OK] Grouped {len(all_providers)} providers into {len(grouped_by_location)} locations")
        print(f"[OK] Output written to: {output_file}")
    
    return output_data


def main():
    """Main function to run the script."""
    import sys
    
    input_file = 'ucship_anthem_providers_grouped_2026-01-10.json'
    output_file = 'ucship_anthem_providers_by_address.json'
    use_base_address = False
    
    # Allow command line arguments
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    if len(sys.argv) > 3:
        use_base_address = sys.argv[3].lower() in ('true', '1', 'yes', 'base')
    
    try:
        result = group_providers_by_address(input_file, output_file, use_base_address=use_base_address)
        
        # Print summary statistics
        print("\n" + "="*60)
        print("GROUPING SUMMARY")
        print("="*60)
        print(f"Total providers: {result['meta_grouped']['total_providers']}")
        print(f"Total locations: {result['meta_grouped']['total_locations']}")
        print(f"Average providers per location: {result['meta_grouped']['total_providers'] / result['meta_grouped']['total_locations']:.2f}")
        
        # Show locations with most providers
        locations_by_count = sorted(result['locations'], 
                                   key=lambda x: x['provider_count'], 
                                   reverse=True)
        print("\nTop 10 locations by provider count:")
        for i, loc in enumerate(locations_by_count[:10], 1):
            print(f"  {i}. {loc['location']['full_address']} - {loc['provider_count']} providers")
        
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{input_file}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
