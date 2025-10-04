import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional

from clausewitz.victoria3.model import StateDefinition, CreateState
from clausewitz.victoria3.tokenizer import TokenType, Token, Lexer


@dataclass
class StatesFile:
    """Root structure representing the entire STATES file"""
    states: List[StateDefinition] = field(default_factory=list)

    def add_file(self, states_file: "StatesFile"):
        """Add another StatesFile to this one"""
        self.states.extend(states_file.states)

    def get_state(self, state_id: str) -> Optional[StateDefinition]:
        """Get a state by its ID"""
        for state in self.states:
            if state.state_id == state_id:
                return state
        return None

    def get_states_by_country(self, country: str) -> List[StateDefinition]:
        """Get all states where a country owns provinces"""
        return [state for state in self.states if country in state.get_countries()]

    def get_states_by_homeland(self, culture: str) -> List[StateDefinition]:
        """Get all states where a culture has homeland"""
        return [state for state in self.states if culture in state.homelands]

    def __repr__(self):
        return f"StatesFile(states={len(self.states)})"


class StateParser:
    """Parser for state configuration files"""

    def __init__(self, tokens: List[Token]):
        self.tokens = [t for t in tokens if t.type != TokenType.COMMENT]
        self.pos = 0

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

    def parse(self) -> StatesFile:
        """Parse the entire file"""
        states_file = StatesFile()

        # Expect: STATES = {
        self.expect(TokenType.IDENTIFIER)  # STATES
        self.expect(TokenType.EQUALS)
        self.expect(TokenType.LBRACE)

        # Parse states
        while self.current_token().type != TokenType.RBRACE:
            state = self.parse_state()
            states_file.states.append(state)

        self.expect(TokenType.RBRACE)
        return states_file

    def parse_state(self) -> StateDefinition:
        """Parse a state block: s:STATE_NAME = { ... }"""
        # Expect: s
        prefix = self.expect(TokenType.IDENTIFIER)
        if prefix.value != 's':
            self.error(f"Expected state prefix 's', got '{prefix.value}'")

        # Expect: :
        self.expect(TokenType.COLON)

        # Expect: STATE_ID
        state_id = self.expect(TokenType.IDENTIFIER).value

        # Expect: =
        self.expect(TokenType.EQUALS)

        # Expect: {
        self.expect(TokenType.LBRACE)

        state = StateDefinition(state_id=state_id)

        # Parse state contents
        while self.current_token().type != TokenType.RBRACE:
            keyword_token = self.current_token()

            if keyword_token.type != TokenType.IDENTIFIER:
                self.error(f"Expected identifier, got {keyword_token.type.value}")

            keyword = keyword_token.value

            if keyword == 'create_state':
                create_state = self.parse_create_state()
                state.create_states.append(create_state)
            elif keyword == 'add_homeland':
                culture = self.parse_add_homeland()
                state.homelands.append(culture)
            elif keyword == 'add_claim':
                country = self.parse_add_claim()
                state.claims.append(country)
            else:
                self.error(f"Unknown keyword: {keyword}")

        # Expect: }
        self.expect(TokenType.RBRACE)

        return state

    def parse_create_state(self) -> CreateState:
        """Parse a create_state block: create_state = { ... }"""
        # Expect: create_state
        self.expect(TokenType.IDENTIFIER)

        # Expect: =
        self.expect(TokenType.EQUALS)

        # Expect: {
        self.expect(TokenType.LBRACE)

        create_state = None

        # Parse properties
        while self.current_token().type != TokenType.RBRACE:
            prop_name_token = self.current_token()

            if prop_name_token.type != TokenType.IDENTIFIER:
                self.error(f"Expected property name, got {prop_name_token.type.value}")

            prop_name = self.advance().value
            self.expect(TokenType.EQUALS)

            if prop_name == 'country':
                # country = c:TAG
                self.expect(TokenType.IDENTIFIER)  # 'c'
                self.expect(TokenType.COLON)
                country_tag = self.expect(TokenType.IDENTIFIER).value
                create_state = CreateState(country=country_tag)

            elif prop_name == 'owned_provinces':
                if create_state is None:
                    self.error("'country' must be defined before 'owned_provinces'")

                # owned_provinces = { x123 x456 ... }
                self.expect(TokenType.LBRACE)

                while self.current_token().type != TokenType.RBRACE:
                    province_token = self.current_token()

                    if province_token.type == TokenType.IDENTIFIER:
                        province_id = self.advance().value
                        create_state.owned_provinces.append(province_id)
                    else:
                        self.error(f"Expected province ID, got {province_token.type.value}")

                self.expect(TokenType.RBRACE)

            elif prop_name == 'state_type':
                if create_state is None:
                    self.error("'country' must be defined before 'state_type'")

                state_type = self.expect(TokenType.IDENTIFIER).value
                create_state.state_type = state_type

            else:
                self.error(f"Unknown property: {prop_name}")

        # Expect: }
        self.expect(TokenType.RBRACE)

        if create_state is None:
            self.error("create_state block must have a 'country' property")

        return create_state

    def parse_add_homeland(self) -> str:
        """Parse an add_homeland statement: add_homeland = cu:CULTURE"""
        # Expect: add_homeland
        self.expect(TokenType.IDENTIFIER)

        # Expect: =
        self.expect(TokenType.EQUALS)

        # Expect: cu
        self.expect(TokenType.IDENTIFIER)

        # Expect: :
        self.expect(TokenType.COLON)

        # Expect: CULTURE
        culture = self.expect(TokenType.IDENTIFIER).value

        return culture

    def parse_add_claim(self) -> str:
        """Parse an add_claim statement: add_claim = c:COUNTRY"""
        # Expect: add_claim
        self.expect(TokenType.IDENTIFIER)

        # Expect: =
        self.expect(TokenType.EQUALS)

        # Expect: c
        self.expect(TokenType.IDENTIFIER)

        # Expect: :
        self.expect(TokenType.COLON)

        # Expect: COUNTRY
        country = self.expect(TokenType.IDENTIFIER).value

        return country

    def parse_file(self) -> StatesFile:
        """Main entry point for parsing"""
        return self.parse()


def parse_states_file(file_path: str | Path) -> StatesFile:
    """
    Parse a STATES configuration file

    Args:
        file_path: Path to the file to parse

    Returns:
        StatesFile object representing the parsed data
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lexer = Lexer(content)
    tokens = lexer.tokenize()

    parser = StateParser(tokens)
    return parser.parse_file()


def parse_states_string(content: str) -> StatesFile:
    """
    Parse a STATES configuration string

    Args:
        content: String content to parse

    Returns:
        StatesFile object representing the parsed data
    """
    lexer = Lexer(content)
    tokens = lexer.tokenize()

    parser = StateParser(tokens)
    return parser.parse_file()


# Utility functions
def print_state_statistics(states_file: StatesFile):
    """Print statistics about the parsed states file"""
    print(f"Total States: {len(states_file.states)}")

    total_provinces = sum(state.get_total_provinces() for state in states_file.states)
    total_create_states = sum(len(state.create_states) for state in states_file.states)

    print(f"Total create_state blocks: {total_create_states}")
    print(f"Total Provinces: {total_provinces}")

    # Count states by country
    country_counts: Dict[str, int] = {}
    for state in states_file.states:
        for country in state.get_countries():
            country_counts[country] = country_counts.get(country, 0) + 1

    print(f"\nUnique Countries: {len(country_counts)}")


def get_provinces_by_country(states_file: StatesFile) -> Dict[str, List[str]]:
    """Get all provinces owned by each country"""
    result: Dict[str, List[str]] = {}

    for state in states_file.states:
        for create_state in state.create_states:
            if create_state.country not in result:
                result[create_state.country] = []
            result[create_state.country].extend(create_state.owned_provinces)

    return result


def get_state_homelands(states_file: StatesFile) -> Dict[str, List[str]]:
    """Get all states for each culture's homeland"""
    result: Dict[str, List[str]] = {}

    for state in states_file.states:
        for culture in state.homelands:
            if culture not in result:
                result[culture] = []
            result[culture].append(state.state_id)

    return result


# Example usage
if __name__ == "__main__":
    # Parse from file
    state_dir = Path("../../../nations_released/game/common/history/states")
    states = StatesFile()
    for f in os.listdir(state_dir):
        if f.endswith(".txt"):
            file_pops = parse_states_file(state_dir / f)
            states.add_file(file_pops)

    # Print statistics
    print_state_statistics(states)

    # Get specific state
    state = states.get_state("STATE_NEW_YORK")
    if state:
        print(f"\n{state}")
        print(f"Countries: {state.get_countries()}")
        print(f"Homelands: {state.homelands}")
        print(f"Total Provinces: {state.get_total_provinces()}")
        for cs in state.create_states:
            print(f"  {cs}")

    # Get states by country
    usa_states = states.get_states_by_country("USA")
    print(f"\nUSA owns provinces in {len(usa_states)} states")

    # Get homeland distribution
    homelands = get_state_homelands(states)
    print("\nTop 10 Cultures by Number of Homeland States:")
    for culture, state_list in sorted(homelands.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"  {culture}: {len(state_list)} states")

    # Get province counts by country
    provinces = get_provinces_by_country(states)
    print("\nTop 10 Countries by Province Count:")
    for country, prov_list in sorted(provinces.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"  {country}: {len(prov_list):,} provinces")
