import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional

from clausewitz.victoria3.model import PopEntry, RegionState, PopState
from clausewitz.victoria3.tokenizer import TokenType, Token, Lexer


@dataclass
class PopFile:
    """Root structure representing the entire POPS file"""
    filename: str
    states: List[PopState] = field(default_factory=list)

    def add_file(self, pop_file: "PopFile"):
        """Add another PopFile to this one"""
        self.states.extend(pop_file.states)

    def get_state(self, state_id: str) -> Optional[PopState]:
        """Get a state by its ID"""
        for state in self.states:
            if state.state_id == state_id:
                return state
        return None

    def __repr__(self):
        return f"PopFile(states={len(self.states)})"


class Parser:
    """Parser for the configuration file"""

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

    def parse(self) -> PopFile:
        """Parse the entire file"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        lexer = Lexer(content)
        tokens = lexer.tokenize()

        self.tokens = [t for t in tokens if t.type != TokenType.COMMENT]  # Filter out comments
        self.pos = 0
        pops_file = PopFile(os.path.basename(self.file_path))

        # Expect: POPS = {
        self.expect(TokenType.IDENTIFIER)  # POPS
        self.expect(TokenType.EQUALS)
        self.expect(TokenType.LBRACE)

        # Parse states
        while self.current_token().type != TokenType.RBRACE:
            state = self.parse_state()
            pops_file.states.append(state)

        self.expect(TokenType.RBRACE)
        return pops_file

    def parse_state(self) -> PopState:
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

        state = PopState(state_id=state_id)

        # Parse region_states
        while self.current_token().type != TokenType.RBRACE:
            region_state = self.parse_region_state()
            state.region_states.append(region_state)

        # Expect: }
        self.expect(TokenType.RBRACE)

        return state

    def parse_region_state(self) -> RegionState:
        """Parse a region_state block: region_state:TAG = { ... }"""
        # Expect: region_state
        prefix = self.expect(TokenType.IDENTIFIER)
        if prefix.value != 'region_state':
            self.error(f"Expected 'region_state', got '{prefix.value}'")

        # Expect: :
        self.expect(TokenType.COLON)

        # Expect: COUNTRY_TAG
        country_tag = self.expect(TokenType.IDENTIFIER).value

        # Expect: =
        self.expect(TokenType.EQUALS)

        # Expect: {
        self.expect(TokenType.LBRACE)

        region_state = RegionState(country_tag=country_tag)

        # Parse create_pop blocks
        while self.current_token().type != TokenType.RBRACE:
            pop = self.parse_create_pop()
            region_state.populations.append(pop)

        # Expect: }
        self.expect(TokenType.RBRACE)

        return region_state

    def parse_create_pop(self) -> PopEntry:
        """Parse a create_pop block: create_pop = { ... }"""
        # Expect: create_pop
        keyword = self.expect(TokenType.IDENTIFIER)
        if keyword.value != 'create_pop':
            self.error(f"Expected 'create_pop', got '{keyword.value}'")

        # Expect: =
        self.expect(TokenType.EQUALS)

        # Expect: {
        self.expect(TokenType.LBRACE)

        pop = PopEntry()

        # Parse properties
        while self.current_token().type != TokenType.RBRACE:
            prop_name = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.EQUALS)
            prop_value_token = self.current_token()

            if prop_value_token.type == TokenType.IDENTIFIER:
                prop_value = self.advance().value
            elif prop_value_token.type == TokenType.NUMBER:
                prop_value = self.advance().value
            else:
                self.error(f"Expected identifier or number for property value")

            # Set property on PopEntry
            if prop_name == 'culture':
                pop.culture = prop_value
            elif prop_name == 'religion':
                pop.religion = prop_value
            elif prop_name == 'size':
                pop.size = prop_value
            elif prop_name == 'pop_type':
                pop.pop_type = prop_value
            else:
                self.error(f"Unknown property: {prop_name}")

        # Expect: }
        self.expect(TokenType.RBRACE)

        return pop


def parse_pop_file(file_path: str | Path) -> PopFile:
    """
    Parse a POPS configuration file

    Args:
        file_path: Path to the file to parse

    Returns:
        PopsFile object representing the parsed data
    """

    return Parser(file_path).parse()


# def parse_pops_string(content: str) -> PopFile:
#     """
#     Parse a POPS configuration string
#
#     Args:
#         content: String content to parse
#
#     Returns:
#         PopsFile object representing the parsed data
#     """
#     lexer = Lexer(content)
#     tokens = lexer.tokenize()
#
#     parser = Parser(tokens)
#     return parser.parse()


# Example usage and utility functions
def print_statistics(pop_files: list[PopFile]):
    """Print statistics about the parsed file"""
    pop_states = [state for f in pop_files for state in f.states]
    print(f"Total States: {len(pop_states)}")

    total_pops = 0
    total_regions = 0

    for state in pop_states:
        total_regions += len(state.region_states)
        for region in state.region_states:
            total_pops += len(region.populations)

    print(f"Total Region States: {total_regions}")
    print(f"Total Population Entries: {total_pops}")


def get_total_population_by_state(pops_file: PopFile) -> Dict[str, int]:
    """Calculate total population for each state"""
    result = {}

    for state in pops_file.states:
        total = 0
        for region in state.region_states:
            for pop in region.populations:
                if pop.size:
                    total += pop.size
        result[state.state_id] = total

    return result


def get_populations_by_culture(pop_files: list[PopFile]) -> Dict[str, int]:
    """Calculate total population for each culture"""
    result = {}
    pop_states = [state for f in pop_files for state in f.states]

    for state in pop_states:
        for region in state.region_states:
            for pop in region.populations:
                if pop.culture and pop.size:
                    result[pop.culture] = result.get(pop.culture, 0) + pop.size

    return result


# Example usage:
if __name__ == "__main__":
    # Parse from file
    pop_files: list[PopFile] = []
    pop_dir = Path("../../../nations_released/game/common/history/pops")
    for f in os.listdir(pop_dir):
        if f.endswith(".txt"):
            pop_file = parse_pop_file(pop_dir / f)
            pop_files.append(pop_file)

    # Print statistics
    pops = [state for f in pop_files for state in f.states]
    print_statistics(pop_files)

    # Get specific state
    # state = pop_files.get_state("STATE_NEW_YORK")
    # if state:
    #     print(f"\nState: {state.state_id}")
    #     for region in state.region_states:
    #         print(f"  Region: {region.country_tag}")
    #         for pop in region.populations:
    #             print(f"    {pop}")

    # Get population by culture
    cultures = get_populations_by_culture(pop_files)
    print("\nTop 20 Cultures by Population:")
    for culture, pop in sorted(cultures.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {culture}: {pop:,}")
