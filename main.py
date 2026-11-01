#!/usr/bin/env python3

import argparse
import re
import logging
import os
import sys
import chardet
from faker import Faker
from faker.providers import phone_number
import secrets

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Initialize Faker with a seed for reproducibility
# I seed Faker once, at import, from a secrets draw. Fake numbers therefore
# differ on every run and cannot be reproduced later from a known seed,
# which is what I want when the fakes stand in for real numbers.
fake = Faker()
Faker.seed(secrets.randbits(32))  # Use secrets for better randomness


def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.
    """
    parser = argparse.ArgumentParser(
        description="Masks or replaces phone numbers in text and data files."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input file to process.",
    )
    parser.add_argument(
        "-o",
        "--output_file",
        help="Path to the output file. Required unless --in-place is given. An output path that resolves to the input file is refused.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input file in place. Only applies when -o is not given.",
    )
    parser.add_argument(
        "-m",
        "--mask_char",
        default="X",
        help="Character to use for masking phone numbers. Defaults to 'X'.",
    )
    parser.add_argument(
        "-r",
        "--replace",
        action="store_true",
        help="Replace phone numbers with fake phone numbers.",
    )
    parser.add_argument(
        "-k",
        "--keep_area_code",
        action="store_true",
        help="Keep the original area code when replacing or masking phone numbers.",
    )
    parser.add_argument(
        "--log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level. Defaults to INFO.",
    )

    return parser.parse_args()


# The whole file is read as bytes for detection, then read again as text.
# That double read is the price of trusting chardet over assuming utf-8.
def detect_encoding(file_path):
    """
    Detects the encoding of a file using chardet.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The detected encoding, or None if detection fails.
    """
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            return result["encoding"]
    except Exception as e:
        logging.error(f"Error detecting encoding: {e}")
        return None


# These are digit positions, not character positions. Separators do not
# advance the count, so the same set works for 555-123-4567, (555) 123 4567,
# and 15551234567 alike. The 11 digit case skips digit zero because that is
# the country code, and the area code is the three digits after it.
def _area_digit_indexes(phone_number):
    digits = [c for c in phone_number if c.isdigit()]
    if len(digits) == 11 and digits[0] == "1":
        return {1, 2, 3}
    return {0, 1, 2}


def _extract_area_code(phone_number):
    digits = [c for c in phone_number if c.isdigit()]
    if len(digits) == 11 and digits[0] == "1":
        return "".join(digits[1:4])
    if len(digits) >= 3:
        return "".join(digits[0:3])
    return None


# I walk the original string and keep its separators untouched, swapping
# only digits. The masked result keeps the shape of the number, which
# matters when the file is a fixed layout export.
def mask_phone_number(phone_number, mask_char="X", keep_area_code=False):
    area = _area_digit_indexes(phone_number) if keep_area_code else set()
    out = []
    idx = -1
    for char in phone_number:
        if char.isdigit():
            idx += 1
            out.append(char if idx in area else mask_char)
        else:
            out.append(char)
    return "".join(out)


def replace_phone_number(phone_number, keep_area_code=False):
    """
    Replaces a phone number with a fake one.

    Args:
        phone_number (str): The phone number to replace.
        keep_area_code (bool): Whether to keep the original area code. Defaults to False.

    Returns:
        str: The replaced phone number.
    """
    try:
        # Extract area code if requested and possible.  Handle cases where number doesn't
        # neatly divide into area code / prefix/ line number.  This regex is more permissive
        # than the matching one used in find_phone_numbers, because we're trying to *extract*
        # something here.  The more restrictive one in find_phone_numbers is more security focused,
        # as it will avoid false positives.
        area_code = _extract_area_code(phone_number) if keep_area_code else None

        if keep_area_code and area_code:
            new_number = fake.phone_number()

            new_match = re.match(r"(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})", new_number)

            if new_match:
                replaced_number = area_code + "-" + new_match.group(2) + "-" + new_match.group(3)
            else:
                logging.warning("Failed to parse a generated phone number, using a full generated number.")
                replaced_number = fake.phone_number()

        else:
            replaced_number = fake.phone_number()

        return replaced_number
    except Exception as e:
        logging.error(f"Error replacing phone number: {e}")
        return phone_number  # Return original if replacement fails


def find_phone_numbers(text):
    """
    Finds phone numbers in the given text using regular expressions.  This is deliberately quite strict,
    to avoid false positives which could lead to data corruption.

    Args:
        text (str): The text to search.

    Returns:
        list: A list of phone numbers found in the text.
    """
    # The lookarounds refuse matches glued to more digits, so a longer ID or
    # account number that happens to contain a phone-shaped run is left alone.
    # I would rather miss an oddly written number than corrupt a longer value.
    pattern = re.compile(
        r"(?<!\d)(?:\+?1[\s.\-]?)?(?:\(\d{3}\)\s?|\d{3}[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)"
    )
    seen = []
    for m in pattern.finditer(text):
        # Dedupe matters beyond tidiness. Processing replaces every occurrence of
        # each string in this list, so one entry per distinct formatting keeps a
        # repeated number mapped to the same fake everywhere it appears.
        if m.group(0) not in seen:
            seen.append(m.group(0))
    return seen


def process_file(input_file, output_file=None, mask_char="X", replace=False, keep_area_code=False):
    """
    Processes the input file, masking or replacing phone numbers, and writes the output to a file.

    Args:
        input_file (str): Path to the input file.
        output_file (str): Path to the output file. If None, overwrites the input file.
        mask_char (str): Character to use for masking.
        replace (bool): Whether to replace phone numbers with fake ones.
        keep_area_code (bool): Whether to keep the original area code when replacing.
    """
    if not os.path.exists(input_file):
        logging.error(f"Input file not found: {input_file}")
        sys.exit(1)

    encoding = detect_encoding(input_file)
    if not encoding:
        logging.error("Failed to detect file encoding.  Please specify encoding if errors occur.")
        # Detection failing is not fatal here. I fall back to utf-8 and log it, and
        # the output is written in that same encoding, not the detected one.
        encoding = "utf-8"  # Fallback to utf-8

    try:
        with open(input_file, "r", encoding=encoding) as f:
            content = f.read()
    except Exception as e:
        logging.error(f"Error reading input file: {e}")
        sys.exit(1)

    phone_numbers = find_phone_numbers(content)
    # I count occurrences before replacing anything. After the first replace
    # pass the original strings are gone and the count could not be rebuilt.
    total = sum(content.count(p) for p in phone_numbers)
    logging.debug(f"Found phone numbers: count={len(phone_numbers)}")
    logging.info(f"Found {total} phone number occurrence(s).")
    if total == 0:
        logging.error("No phone numbers found; nothing was masked or replaced.")
        sys.exit(1)

    for phone_number in phone_numbers:
        position = content.find(phone_number)
        if replace:
            replacement = replace_phone_number(phone_number, keep_area_code)
            logging.info(f"Replacing phone number at position {position} (count only, value not logged).")
            # String replace hits every occurrence at once. In replace mode a fake
            # number written by an earlier pass could in principle be matched by a
            # later pass if it equals another listed number; I have not seen it happen,
            # but the order of this loop is why it stays a theoretical risk.
            content = content.replace(phone_number, replacement)
        else:
            masked_number = mask_phone_number(phone_number, mask_char, keep_area_code=keep_area_code)
            logging.info(f"Masking phone number at position {position} (count only, value not logged).")
            content = content.replace(phone_number, masked_number)

    if output_file is None:
        output_file = input_file  # Overwrite input file if no output file is specified

    try:
        with open(output_file, "w", encoding=encoding) as f:
            f.write(content)
        logging.info(f"Processed file saved to: {output_file}")
    except Exception as e:
        logging.error(f"Error writing output file: {e}")
        sys.exit(1)


def main():
    """
    Main function to execute the phone number masking/replacement process.
    """
    args = setup_argparse()

    # Set logging level
    logging.getLogger().setLevel(args.log_level)

    logging.debug(f"Arguments: {args}")

    input_file = args.input_file
    if args.output_file:
        if os.path.realpath(args.output_file) == os.path.realpath(input_file):
            logging.error("Output file resolves to the input file; refusing to overwrite it. Use --in-place to overwrite intentionally.")
            sys.exit(1)
        output_file = args.output_file
    elif getattr(args, "in_place", False):
        # In process_file, None is the overwrite signal, not a missing value. The
        # --in-place branch passes None on purpose so the input path is reused.
        output_file = None
    else:
        logging.error("No output file given. Pass -o for an output file or --in-place to overwrite the input file.")
        sys.exit(1)
    mask_char = args.mask_char
    replace = args.replace
    keep_area_code = args.keep_area_code

    # Input Validation
    # Checked late, after argument parsing, because argparse cannot express a
    # one character string on its own. A longer mask would change the length
    # of every number it touched and break fixed layouts silently.
    if len(mask_char) != 1:
        logging.error("Mask character must be a single character.")
        sys.exit(1)

    try:
        process_file(input_file, output_file, mask_char, replace, keep_area_code)
    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()