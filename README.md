# dso-phone-number-masker
Masks or replaces phone numbers in text and data files, preserving format and area code consistency (where possible) to maintain data usability for analysis after sanitization. - Focused on Tools for sanitizing and obfuscating sensitive data within text files and structured data formats

## Install
`git clone https://github.com/ShadowStrikeHQ/dso-phone-number-masker`

## Usage
`./dso-phone-number-masker [params]`

## Parameters
- `-h`: Show help message and exit
- `-o`: Path to the output file. If not specified, overwrites the input file.
- `-m`: Character to use for masking phone numbers. Defaults to 
- `-r`: Replace phone numbers with fake phone numbers.
- `-k`: Keep the original area code when replacing or masking phone numbers.
- `--log_level`: Set the logging level. Defaults to INFO.

## License
Copyright (c) ShadowStrikeHQ
