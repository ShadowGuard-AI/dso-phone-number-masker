![Banner](banner.png)

# dso-phone-number-masker
Masks or replaces phone numbers in text and data files, preserving format and area code consistency (where possible) to maintain data usability for analysis after sanitization. - Focused on Tools for sanitizing and obfuscating sensitive data within text files and structured data formats

## Install
`git clone https://github.com/ShadowStrikeHQ/dso-phone-number-masker`

## Usage
`./dso-phone-number-masker [params]`

## Parameters
- `-h`: Show help message and exit
- `-o`: Path to the output file. Required unless `--in-place` is given. An output path that resolves to the input file is refused at exit 1.
- `--in-place`: Overwrite the input file in place. Only applies when `-o` is not given. Without `-o` or `--in-place`, the run exits 1 and writes nothing.
- `-m`: Character to use for masking phone numbers. Defaults to X
- `-r`: Replace phone numbers with fake phone numbers.
- `-k`: Keep the original area code (the first three digits of the number itself, after any +1 country code) when replacing or masking phone numbers.
- `--log_level`: Set the logging level. Defaults to INFO. At every level the tool logs counts and positions only, never an original phone number.

Detected forms include plain numbers such as 312-555-0147, parenthesised area codes such as (312) 555-0147, and an optional leading +1 country code, which is included in the match so no part of a matched number is left in clear. A run that finds no phone numbers exits 1, prints no saved line, and writes no output file.

## License
Copyright (c) ShadowStrikeHQ
