import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Literal

from clausewitz.victoria3 import logging_utils
from clausewitz.victoria3.tokenizer import TokenType, Token, Lexer


logger = logging_utils.get_logger(__name__, "DEBUG")


@dataclass
class RGBColor:
    red: int
    green: int
    blue: int

    def __init__(self, red: int, green: int, blue: int):
        self.red = red
        self.green = green
        self.blue = blue

    def __str__(self):
        return f"RGB({self.red}, {self.green}, {self.blue})"


@dataclass
class HSVColor:
    hue: float
    saturation: float
    value: float

    def __init__(self, hue: float, saturation: float, value: float):
        self.hue = hue
        self.saturation = saturation
        self.value = value

    def __str__(self):
        return f"HSV({self.hue}, {self.saturation}, {self.value})"


Color = RGBColor | HSVColor


@dataclass
class CountryDef:
    """Represents a country definition"""
    tag: str
    color: Optional[Color] = None
    cultures: List[str] = field(default_factory=list)
    religion: Optional[str] = None
    capital: Optional[str] = None
    tier: Optional[str] = None
    is_named_from_capital: bool = False
    dynamic_country_definition: bool = False

    def __repr__(self):
        return f"CountryDefinition(tag={self.tag}, cultures={self.cultures}, capital={self.capital})"


@dataclass
class CountryFile:
    """Root structure representing the entire countries file"""
    filename: str
    countries: List[CountryDef] = field(default_factory=list)

    def get_country(self, tag: str) -> Optional[CountryDef]:
        """Get a country by its tag"""
        for country in self.countries:
            if country.tag == tag:
                return country
        return None

    def get_countries_by_culture(self, culture: str) -> List[CountryDef]:
        """Get all countries that have the specified culture"""
        return [country for country in self.countries if culture in country.cultures]

    def __repr__(self):
        return f"CountriesFile(countries={len(self.countries)})"


class CountryParser:
    """Parser for country definition files"""

    def __init__(self, file_path: Path):
        self.file_path = file_path

    def error(self, msg: str):
        token = self.current_token()
        raise SyntaxError(f"Parser error at line {token.line}, column {token.column}: {msg}")

    def current_token(self) -> Token:
        """Get current token"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]  # EOF

    def peek_token(self, offset: int = 0) -> Token:
        """Peek at token at current position + offset"""
        pos = self.pos + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1]  # EOF

    def advance(self) -> Token:
        """Advance to next token and return current"""
        token = self.current_token()
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token

    def expect(self, token_type: TokenType) -> Token:
        """Expect a specific token type and advance"""
        token = self.current_token()
        if token.type != token_type:
            self.error(f"Expected {token_type.value}, got {token.type.value}")
        return self.advance()

    def parse(self) -> CountryFile:
        """Parse the entire file"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        lexer = Lexer(content)
        tokens = lexer.tokenize()

        self.tokens = [t for t in tokens if t.type != TokenType.COMMENT]  # Filter out comments
        self.pos = 0
        country_file = CountryFile(os.path.basename(self.file_path))

        # Parse countries until EOF
        while self.current_token().type != TokenType.EOF:
            country = self.parse_country()
            if country:
                country_file.countries.append(country)

        return country_file

    def parse_country(self) -> Optional[CountryDef]:
        """Parse a country block: TAG = { ... }"""
        # Expect: TAG (3-letter country code)
        tag_token = self.current_token()

        if tag_token.type == TokenType.EOF:
            return None

        if tag_token.type != TokenType.IDENTIFIER:
            self.error(f"Expected country tag identifier, got {tag_token.type.value}")

        tag = self.advance().value

        # Expect: =
        self.expect(TokenType.EQUALS)

        # Expect: {
        self.expect(TokenType.LBRACE)

        country = CountryDef(tag=tag)

        # Parse country properties
        while self.current_token().type != TokenType.RBRACE:
            prop_name_token = self.current_token()

            if prop_name_token.type != TokenType.IDENTIFIER:
                self.error(f"Expected property name, got {prop_name_token.type.value}")

            prop_name = self.advance().value
            self.expect(TokenType.EQUALS)

            if prop_name == 'cultures':
                # cultures = { culture1 culture2 ... }
                self.expect(TokenType.LBRACE)
                cultures = []
                while self.current_token().type != TokenType.RBRACE:
                    culture_token = self.current_token()
                    if culture_token.type == TokenType.IDENTIFIER:
                        cultures.append(self.advance().value)
                    else:
                        self.error(f"Expected culture identifier, got {culture_token.type.value}")
                self.expect(TokenType.RBRACE)
                country.cultures = cultures

            elif prop_name == 'color':
                next_token = self.peek_token()
                is_hsv = False
                if next_token.type == TokenType.IDENTIFIER:
                    self.advance()
                    if next_token.value != 'hsv':
                        logger.warning(f"Unknown color scheme, treating as hsv: {next_token.value}")
                    is_hsv = True

                self.expect(TokenType.LBRACE)
                color_args = []
                while self.current_token().type != TokenType.RBRACE:
                    color_arg_token = self.current_token()
                    if color_arg_token.type == TokenType.NUMBER:
                        val = int(color_arg_token.value) if not is_hsv else float(color_arg_token.value)
                        color_args.append(val)
                        self.advance()
                    else:
                        self.error(f"Expected number, got {color_arg_token.type.value}")

                self.expect(TokenType.RBRACE)
                color = HSVColor(*color_args) if is_hsv else RGBColor(*color_args)
                country.color = color

            elif prop_name == 'religion':
                country.religion = self.expect(TokenType.IDENTIFIER).value

            elif prop_name == 'capital':
                # capital = STATE_NAME
                country.capital = self.expect(TokenType.IDENTIFIER).value

            elif prop_name == 'tier':
                # tier = TIER_TYPE
                country.tier = self.expect(TokenType.IDENTIFIER).value

            elif prop_name == 'is_named_from_capital':
                # is_named_from_capital = yes/no
                value = self.expect(TokenType.IDENTIFIER).value
                country.is_named_from_capital = (value == 'yes')

            elif prop_name == 'dynamic_country_definition':
                # dynamic_country_definition = yes/no
                value = self.expect(TokenType.IDENTIFIER).value
                country.dynamic_country_definition = (value == 'yes')

            elif prop_name == 'country_type':
                # country_type = TYPE (skip for now)
                self.expect(TokenType.IDENTIFIER)

            else:
                # Skip unknown properties - consume until next property or end of block
                # This could be a simple value or a nested block
                next_token = self.current_token()
                if next_token.type == TokenType.LBRACE:
                    self.skip_block()
                elif next_token.type == TokenType.IDENTIFIER or next_token.type == TokenType.NUMBER:
                    self.advance()
                else:
                    self.error(f"Unknown property: {prop_name}")

        # Expect: }
        self.expect(TokenType.RBRACE)

        return country

    def skip_block(self):
        """Skip a nested block { ... }"""
        self.expect(TokenType.LBRACE)
        depth = 1
        while depth > 0 and self.current_token().type != TokenType.EOF:
            token = self.advance()
            if token.type == TokenType.LBRACE:
                depth += 1
            elif token.type == TokenType.RBRACE:
                depth -= 1


def parse_country_file(file_path: str | Path) -> CountryFile:
    """
    Parse a country definitions configuration file

    Args:
        file_path: Path to the file to parse

    Returns:
        CountryFile object representing the parsed data
    """
    return CountryParser(file_path).parse()


# Utility functions
def print_country_statistics(country_files: list[CountryFile]):
    """Print statistics about the parsed country files"""
    all_countries = [country for f in country_files for country in f.countries]
    print(f"Total Countries: {len(all_countries)}")

    dynamic_countries = [c for c in all_countries if c.dynamic_country_definition]
    print(f"Dynamic Country Definitions: {len(dynamic_countries)}")
    print(f"Static Country Definitions: {len(all_countries) - len(dynamic_countries)}")

    # Count countries by number of cultures
    single_culture = [c for c in all_countries if len(c.cultures) == 1]
    multi_culture = [c for c in all_countries if len(c.cultures) > 1]
    no_culture = [c for c in all_countries if len(c.cultures) == 0]

    print(f"\nCountries by Culture Count:")
    print(f"  Single culture: {len(single_culture)}")
    print(f"  Multiple cultures: {len(multi_culture)}")
    print(f"  No cultures: {len(no_culture)}")


def get_cultures_by_country_count(countries_files: list[CountryFile]) -> dict[str, int]:
    """Get count of countries for each culture"""
    all_countries = [country for f in countries_files for country in f.countries]
    culture_counts = {}

    for country in all_countries:
        for culture in country.cultures:
            culture_counts[culture] = culture_counts.get(culture, 0) + 1

    return culture_counts


def get_countries_by_tier(countries_files: list[CountryFile]) -> dict[str, list[str]]:
    """Group countries by their tier"""
    all_countries = [country for f in countries_files for country in f.countries]
    by_tier = {}

    for country in all_countries:
        tier = country.tier or "none"
        if tier not in by_tier:
            by_tier[tier] = []
        by_tier[tier].append(country.tag)

    return by_tier


# Example usage
if __name__ == "__main__":
    # Parse from file
    country_files: list[CountryFile] = []
    country_dir = Path("../../../game/common/country_definitions")

    if country_dir.exists():
        for f in os.listdir(country_dir):
            if f.endswith(".txt"):
                country_file = parse_country_file(country_dir / f)
                country_files.append(country_file)

        # Print statistics
        print_country_statistics(country_files)

        # Get culture distribution
        cultures = get_cultures_by_country_count(country_files)
        print("\nTop 20 Cultures by Country Count:")
        for culture, count in sorted(cultures.items(), key=lambda x: x[1], reverse=True)[:20]:
            print(f"  {culture}: {count} countries")

        # Get countries by tier
        by_tier = get_countries_by_tier(country_files)
        print("\nCountries by Tier:")
        for tier, countries in sorted(by_tier.items()):
            print(f"  {tier}: {len(countries)} countries")
    else:
        print(f"Country directory not found: {country_dir}")