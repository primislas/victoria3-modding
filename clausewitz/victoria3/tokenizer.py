from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Any


class TokenType(Enum):
    """Token types for lexical analysis"""
    IDENTIFIER = "IDENTIFIER"
    STRING = "STRING"
    NUMBER = "NUMBER"
    EQUALS = "EQUALS"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    COLON = "COLON"
    COMMENT = "COMMENT"
    EOF = "EOF"


@dataclass
class Token:
    """Represents a single token"""
    type: TokenType
    value: Any
    line: int
    column: int


class Lexer:
    """Lexical analyzer for the configuration file"""

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def error(self, msg: str):
        raise SyntaxError(f"Lexer error at line {self.line}, column {self.column}: {msg}")

    def peek(self, offset: int = 0) -> Optional[str]:
        """Peek at character at current position + offset"""
        pos = self.pos + offset
        if pos < len(self.text):
            return self.text[pos]
        return None

    def advance(self) -> Optional[str]:
        """Advance position and return current character"""
        if self.pos < len(self.text):
            char = self.text[self.pos]
            self.pos += 1
            if char == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            return char
        return None

    def skip_whitespace(self):
        """Skip whitespace characters"""
        while self.peek() and self.peek() in ' \t\r\n':
            self.advance()

    def read_comment(self) -> str:
        """Read a comment until end of line"""
        comment = ""
        self.advance()  # skip #
        while self.peek() and self.peek() != '\n':
            comment += self.advance()
        return comment.strip()

    def read_identifier(self) -> str:
        """Read an identifier or keyword"""
        identifier = ""
        while self.peek() and (self.peek().isalnum() or self.peek() in '_'):
            identifier += self.advance()
        return identifier

    def read_string(self) -> str:
        """Read a quoted string"""
        quote_char = self.advance()  # consume opening quote
        string = ""
        while self.peek() and self.peek() != quote_char:
            if self.peek() == '\\':
                self.advance()
                next_char = self.advance()
                if next_char:
                    string += next_char
            else:
                string += self.advance()

        if self.peek() == quote_char:
            self.advance()  # consume closing quote
        else:
            self.error("Unterminated string")

        return string

    def read_number(self) -> int | float:
        """Read a number (integer or float)"""
        num_str = ""
        if self.peek() == '-':
            num_str += self.advance()

        while self.peek() and self.peek().isdigit():
            num_str += self.advance()

        # Check for decimal point
        if self.peek() == '.':
            num_str += self.advance()
            # Read decimal part
            while self.peek() and self.peek().isdigit():
                num_str += self.advance()
            return float(num_str)

        return int(num_str)

    def tokenize(self) -> List[Token]:
        """Tokenize the entire input"""
        self.tokens = []

        while self.pos < len(self.text):
            self.skip_whitespace()

            if self.pos >= len(self.text):
                break

            current_line = self.line
            current_column = self.column
            char = self.peek()

            # Comment
            if char == '#':
                comment = self.read_comment()
                self.tokens.append(Token(TokenType.COMMENT, comment, current_line, current_column))

            # Braces
            elif char == '{':
                self.advance()
                self.tokens.append(Token(TokenType.LBRACE, '{', current_line, current_column))

            elif char == '}':
                self.advance()
                self.tokens.append(Token(TokenType.RBRACE, '}', current_line, current_column))

            # Equals
            elif char == '=':
                self.advance()
                self.tokens.append(Token(TokenType.EQUALS, '=', current_line, current_column))

            # Colon
            elif char == ':':
                self.advance()
                self.tokens.append(Token(TokenType.COLON, ':', current_line, current_column))

            # String
            elif char in '"\'':
                string = self.read_string()
                self.tokens.append(Token(TokenType.STRING, string, current_line, current_column))

            # Number
            elif char.isdigit() or (char == '-' and self.peek(1) and self.peek(1).isdigit()):
                number = self.read_number()
                self.tokens.append(Token(TokenType.NUMBER, number, current_line, current_column))

            # Identifier
            elif char.isalpha() or char == '_':
                identifier = self.read_identifier()
                self.tokens.append(Token(TokenType.IDENTIFIER, identifier, current_line, current_column))

            # Zero-width space
            elif char == '\u200c' or char == '\u200d' or char == '\ufeff':
                self.advance()
            else:
                self.error(f"Unexpected character: {char}")

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens
