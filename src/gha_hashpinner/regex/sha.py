"""Regular expressions for validating Git SHAs."""

import re

# A Git commit sha is 40 hexadecimal characters
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
