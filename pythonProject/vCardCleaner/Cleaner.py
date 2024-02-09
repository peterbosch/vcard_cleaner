import re
import sys
import os


def preprocess_vcard_lines(lines):
    """Preprocess vCard lines to handle entries that span multiple lines."""
    processed_lines = []
    current_line = ""

    for line in lines:
        line = line.rstrip()  # Remove trailing whitespace and newline characters
        if line.startswith(' ') or line.startswith('\t'):  # Continuation of the previous line
            # Remove leading whitespace and concatenate with the previous line
            current_line += line[1:]
        else:
            # If there's a current line being built, add it to the list
            if current_line:
                processed_lines.append(current_line)
            current_line = line
    # Add the last line if it exists
    if current_line:
        processed_lines.append(current_line)

    return processed_lines


def parse_vcard(lines):
    """Parse a single vCard into a dictionary, handling multi-line entries."""
    lines = preprocess_vcard_lines(lines)  # Preprocess lines to handle line continuations
    vcard = {}
    for line in lines:
        if ':' not in line:  # Skip lines without a colon
            continue
        key, value = line.split(':', 1)
        key_parts = key.split(';')
        property_name = key_parts[0]
        params = key_parts[1:] if len(key_parts) > 1 else []
        property_value = {'value': value.strip(), 'params': params}
        if property_name in vcard:
            if isinstance(vcard[property_name], list):
                vcard[property_name].append(property_value)
            else:
                vcard[property_name] = [vcard[property_name], property_value]
        else:
            vcard[property_name] = property_value
    return vcard


def read_vcards(filename):
    """Read vCards from a file and return them as a list of dictionaries."""
    vcards_ = []
    current_vcard = []
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            if line.startswith('BEGIN:VCARD'):
                current_vcard = [line]
            elif line.startswith('END:VCARD'):
                current_vcard.append(line)
                vcards_.append(parse_vcard(current_vcard))
            else:
                current_vcard.append(line)
    return vcards_


def vcard_to_string(vcard):
    """Convert a vCard dictionary back to a vCard string, ensuring BEGIN and END markers are handled correctly."""
    lines = ['BEGIN:VCARD']
    for key, value in vcard.items():
        if key in ['BEGIN', 'END']:  # Skip if BEGIN/END are part of the dictionary for some reason
            continue
        if isinstance(value, list):
            for v in value:
                lines.append(format_vcard_line(key, v))
        else:
            lines.append(format_vcard_line(key, value))
    lines.append('END:VCARD')
    return '\n'.join(lines)


def remove_null_values(vcards_):
    """
    Iterate through all vCards and remove properties or property instances
    with a value of "NULL".
    """
    for vcard in vcards_:
        # Iterate over a list of keys since we're modifying the dictionary
        for key in list(vcard.keys()):
            value = vcard[key]

            if isinstance(value, list):  # For properties with multiple instances
                # Filter out any instances with a value of "NULL"
                filtered_values = [v for v in value if v['value'].upper() != 'NULL']
                if not filtered_values:
                    # If all instances were "NULL", remove the property entirely
                    del vcard[key]
                else:
                    # Otherwise, update the property with the filtered values
                    vcard[key] = filtered_values

            elif isinstance(value, dict):  # For single instance properties
                if value['value'].upper() == 'NULL':
                    # If the single instance has a value of "NULL", remove it
                    del vcard[key]


def extract_name(vcard):
    """Extract first and last name from a vCard. Adjust based on your vCard structure."""
    # This assumes the full name is under the 'FN' property and is a simple string.
    # Adjust this logic based on how your names are actually stored.
    name = vcard.get('FN', {'value': ''})['value']
    parts = name.split(' ')
    first_name = parts[0] if parts else ''
    last_name = parts[-1] if len(parts) > 1 else ''
    return first_name, last_name


def organize_duplicates(vcards_):
    """Organize duplicates into a new dictionary and remove them from the main array."""
    duplicates_ = {}
    unique_vcards_ = []
    seen_names = {}

    for vcard in vcards_:
        first_name, last_name = extract_name(vcard)
        name_key = f"{last_name}, {first_name}"

        # Check if this name has been seen before
        if name_key in seen_names:
            # If seen before, add to duplicates dictionary
            if name_key not in duplicates_:
                duplicates_[name_key] = [seen_names[name_key]]  # Add the first occurrence
            duplicates_[name_key].append(vcard)
        else:
            seen_names[name_key] = vcard
            unique_vcards_.append(vcard)  # Assume it's unique for now

    # Remove vcards that are in duplicates from unique_vcards
    for name_key, vcards_list in duplicates_.items():
        for duplicate_vcard in vcards_list:
            if duplicate_vcard in unique_vcards_:
                unique_vcards_.remove(duplicate_vcard)

    return unique_vcards_, duplicates_


# `unique_vcards` now contains vCards without duplicates
# `duplicates` is a dictionary with "LastName, FirstName" keys and lists of duplicate vCards as values


def remove_identical_entries(duplicates_):
    """
    Removes identical vCard entries under each key in the duplicates' dictionary.
    """
    for key, vcards_ in list(duplicates_.items()):
        unique_vcards_ = []
        seen = set()
        for vcard in vcards_:
            vcard_str = vcard_to_string(vcard)  # Serialize vCard to a string for comparison
            if vcard_str not in seen:
                unique_vcards_.append(vcard)
                seen.add(vcard_str)
        duplicates_[key] = unique_vcards_


def move_unique_entries_back(duplicates_, main_vcards):
    """
    Moves entries with only one vCard back to the main list of vCards.
    """
    for key, vcards_ in list(duplicates_.items()):
        if len(vcards_) == 1:
            main_vcards.append(vcards_[0])  # Add the single vCard back to the main list
            del duplicates_[key]  # Remove the entry from the duplicates dictionary


def clean_duplicates(duplicates_, main_vcards):
    """
    Cleans up the duplicates dictionary by removing all but one of any identical entries
    and moves entries with only one vCard left back to the main list of vCards.
    """
    remove_identical_entries(duplicates_)
    move_unique_entries_back(duplicates_, main_vcards)


# Assuming you have defined vcard_to_string() correctly based on your vCard structure.
# duplicates = {"Doe, John": [...], "Smith, Jane": [...]}
# main_vcards = [...]

# Example usage
# clean_duplicates(duplicates, main_vcards)

def clean_and_aggregate_vcards(duplicates_):
    """
    Cleans each vCard set by removing specified properties and aggregates them into a single vCard.
    """
    item_pattern = re.compile(r'^item\d+\.')  # Regular expression to match "item" followed by digits and a dot

    for key, vcards_ in duplicates_.items():
        aggregated_properties = {}

        for vcard in vcards_:
            for prop, value in list(vcard.items()):
                # Skip properties that match the "item#." pattern
                if item_pattern.match(prop):
                    continue

                # Aggregate unique key/content pairs
                if isinstance(value, list):
                    for v in value:
                        v_str = vcard_to_string({prop: v})  # Serialize for comparison
                        aggregated_properties[v_str] = {prop: v}
                else:
                    v_str = vcard_to_string({prop: value})  # Serialize for comparison
                    aggregated_properties[v_str] = {prop: value}

        # Create a new vCard with aggregated properties
        new_vcard = {}
        for agg_prop in aggregated_properties.values():
            new_vcard.update(agg_prop)

        # Replace the old vCards with the new one
        duplicates_[key] = [new_vcard]


def remove_duplicate_phone_numbers(vcards_):
    """
    Removes duplicate phone number entries from each vCard in the collection.

    :param vcards_: The list of vCards to process.
    """
    for vcard in vcards_:
        if 'TEL' in vcard:  # Check if the vCard has any phone number entries
            unique_phones = {}
            if isinstance(vcard['TEL'], list):
                # Iterate over the list of phone numbers and keep only unique ones
                for phone_entry in vcard['TEL']:
                    phone_number = phone_entry['value']
                    # Use the phone number as the key to ensure uniqueness
                    unique_phones[phone_number] = phone_entry
            else:
                # If there's only one phone entry, it's inherently unique
                unique_phones[vcard['TEL']['value']] = vcard['TEL']

            # Replace the original list of phones with the unique ones
            vcard['TEL'] = list(unique_phones.values())


# Example usage
# Assuming vcards is your list of vCards
# remove_duplicate_phone_numbers(vcards)


def add_duplicates_back_to_vcards(vcards_, duplicates_):
    """
    Adds the aggregated vCard entries from the duplicates dictionary back into the main vCards collection.

    :param vcards_: The main list of vCards to which the aggregated duplicates will be added.
    :param duplicates_: The dictionary of duplicates, where each key has a list with a single aggregated vCard.
    """
    for aggregated_vcards in duplicates_.values():
        # Each key in duplicates should have a list with a single vCard after aggregation
        vcard = aggregated_vcards[0]  # Get the single aggregated vCard
        vcards_.append(vcard)  # Add it back to the main vCards collection


def format_vcard_line(key, value):
    """Format a vCard line from a key and value dictionary."""
    params = ';'.join(value['params']) if value['params'] else ''
    prefix = f"{key};{params}" if params else key
    return f"{prefix}:{value['value']}"


def write_vcards(vcards_, filename):
    """Write vCards to a file, ensuring proper formatting."""
    with open(filename, 'w', encoding='utf-8') as file:
        for vcard in vcards_:
            file.write(vcard_to_string(vcard))
            file.write('\n\n')  # Ensure separation between vCards


def write_vcard_duplicates(duplicates_, directory_name):
    """
    Writes out vCards from a dictionary of duplicates to separate files within a specified directory.

    :param duplicates_: Dictionary of duplicates with "LastName, FirstName" as keys and lists of vCards as values.
    :param directory_name: Name of the directory where the vCard files will be created.
    """
    # Ensure the directory exists
    os.makedirs(directory_name, exist_ok=True)

    for key, vcards_ in duplicates_.items():
        # Sanitize the key to create a valid filename (replace characters not allowed in filenames)
        filename = f"{key.replace(',', '').replace(' ', '_')}.vcf"
        file_path = os.path.join(directory_name, filename)

        # Write the vCards to the file
        with open(file_path, 'w', encoding='utf-8') as file:
            for vcard in vcards_:
                file.write(vcard_to_string(vcard))
                file.write('\n\n')  # Add separation between vCards


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python vcf_processor.py <source_file.vcf>")
        sys.exit(1)

    source_file = sys.argv[1]
    vcards = read_vcards(source_file)  # Assuming this is your parsed vCard data
    remove_null_values(vcards)
    unique_vcards, duplicates = organize_duplicates(vcards)
    clean_duplicates(duplicates, unique_vcards)
    clean_and_aggregate_vcards(duplicates)
    add_duplicates_back_to_vcards(unique_vcards, duplicates)
    remove_duplicate_phone_numbers(unique_vcards)
    write_vcards(unique_vcards, filename="D:/Desktop/unique.vcf")  # Now write the cleaned vCards back to a file
    # write_vcard_duplicates(duplicates, directory_name="D:/Desktop/duplicates.vcf")
    print(f"Processed {len(vcards)} vCards from {source_file} and saved to files.")
