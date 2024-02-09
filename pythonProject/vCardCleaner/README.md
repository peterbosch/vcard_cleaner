# vCard Processing Tool

## Overview
This vCard Processing Tool is designed to assist in managing and cleaning vCard (.vcf) files. It includes features for parsing vCards, removing duplicates, cleaning up entries, and preparing data for import into various contact management systems. The tool is particularly useful for large vCard files where manual editing is impractical.

## Features
- **Parsing vCard Files**: Read vCards from files, supporting the vCard 3.0 specification.
- **Cleaning Data**: Remove entries with null values or specific patterns (e.g., "item#." prefixes).
- **Duplicate Handling**: Identify duplicate vCards based on names, aggregate their unique information, and remove exact duplicates.
- **Phone Number Deduplication**: Ensure each vCard contains only unique phone numbers.
- **Exporting Data**: Write cleaned and processed vCards back to .vcf files, organizing them as needed.

## Getting Started

### Prerequisites
- Python 3.6 or higher

### Installation
Clone this repository to your local machine using:

```bash
git clone https://.git
