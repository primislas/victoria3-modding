import os
from pathlib import Path
from typing import TextIO
from clausewitz.victoria3.parsers.state_parser import StatesFile
from clausewitz.victoria3.model import StateDefinition, CreateState


class StateWriter:
    """Writer for state configuration files"""

    def __init__(self, indent_size: int = 1, use_tabs: bool = True):
        """
        Initialize the writer

        Args:
            indent_size: Number of spaces/tabs per indent level
            use_tabs: Whether to use tabs (True) or spaces (False) for indentation
        """
        self.indent_size = indent_size
        self.use_tabs = use_tabs
        self.indent_char = '\t' if use_tabs else ' '

    def _indent(self, level: int) -> str:
        """Get indentation string for a given level"""
        return self.indent_char * (level * self.indent_size)

    def _write_provinces(self, f: TextIO, provinces: list[str], indent_level: int):
        """Write province list with proper formatting"""
        indent = self._indent(indent_level)

        # Write opening
        f.write(f"{indent}owned_provinces = {{ ")

        # Write provinces on same line with spaces between them
        f.write(' '.join(provinces))

        # Write closing
        f.write(" }\n")

    def _write_create_state(self, f: TextIO, create_state: CreateState, indent_level: int):
        """Write a create_state block"""
        indent = self._indent(indent_level)

        f.write(f"{indent}create_state = {{\n")

        # Write country
        f.write(f"{self._indent(indent_level + 1)}country = c:{create_state.country}\n")

        # Write state_type if present
        if create_state.state_type:
            f.write(f"{self._indent(indent_level + 1)}state_type = {create_state.state_type}\n")

        # Write owned_provinces
        if create_state.owned_provinces:
            self._write_provinces(f, create_state.owned_provinces, indent_level + 1)

        f.write(f"{indent}}}\n")

    def _write_state(self, f: TextIO, state: StateDefinition, indent_level: int):
        """Write a state definition"""
        indent = self._indent(indent_level)

        f.write(f"{indent}s:{state.state_id} = {{\n")

        # Write all create_state blocks
        for create_state in state.create_states:
            self._write_create_state(f, create_state, indent_level + 1)

        # Add blank line after create_state blocks if there are homelands or claims
        if state.create_states and (state.homelands or state.claims):
            f.write("\n")

        # Write add_homeland entries
        for homeland in state.homelands:
            f.write(f"{self._indent(indent_level + 1)}add_homeland = cu:{homeland}\n")

        # Write add_claim entries
        for claim in state.claims:
            f.write(f"{self._indent(indent_level + 1)}add_claim = c:{claim}\n")

        f.write(f"{indent}}}\n")

    def write_to_file(self, states_file: StatesFile, file_path: str | Path):
        """
        Write a StatesFile to a file

        Args:
            states_file: StatesFile object to write
            file_path: Path to the output file
        """
        for state in states_file.states:
            state.merge_states()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            self.write_to_stream(states_file, f)

    def write_to_stream(self, states_file: StatesFile, f: TextIO):
        """
        Write a StatesFile to a stream

        Args:
            states_file: StatesFile object to write
            f: File stream to write to
        """
        # Write header comment
        f.write("# Generated state file\n\n")

        # Write opening
        f.write("STATES = {\n")

        # Write each state
        for state in states_file.states:
            self._write_state(f, state, indent_level=1)

        # Write closing
        f.write("}\n")

    def write_to_string(self, states_file: StatesFile) -> str:
        """
        Write a StatesFile to a string

        Args:
            states_file: StatesFile object to write

        Returns:
            String representation of the file
        """
        from io import StringIO

        stream = StringIO()
        self.write_to_stream(states_file, stream)
        return stream.getvalue()


def write_states_file(states_file: StatesFile, file_path: str | Path,
                      indent_size: int = 1, use_tabs: bool = True):
    """
    Convenience function to write a states file

    Args:
        states_file: StatesFile object to write
        file_path: Path to the output file
        indent_size: Number of spaces/tabs per indent level
        use_tabs: Whether to use tabs (True) or spaces (False)
    """
    writer = StateWriter(indent_size=indent_size, use_tabs=use_tabs)
    writer.write_to_file(states_file, file_path)


def states_to_string(states_file: StatesFile, indent_size: int = 1,
                     use_tabs: bool = True) -> str:
    """
    Convenience function to convert a StatesFile to a string

    Args:
        states_file: StatesFile object to write
        indent_size: Number of spaces/tabs per indent level
        use_tabs: Whether to use tabs (True) or spaces (False)

    Returns:
        String representation of the file
    """
    writer = StateWriter(indent_size=indent_size, use_tabs=use_tabs)
    return writer.write_to_string(states_file)


# Example usage
if __name__ == "__main__":
    from clausewitz.victoria3.parsers.state_parser import parse_states_file

    # Parse an existing file
    # Path("../../../nations_released/game/common/history/states")
    states = parse_states_file("../../../nations_released/game/common/history/states/00_states.txt")

    # Write it back out
    # write_states_file(states, "00_states_output.txt")

    # Or get as string
    output_str = states_to_string(states)
    print(output_str)
    # print(f"Generated {len(output_str)} characters")

    # Example: Create a new state programmatically
    # from clausewitz.victoria3.model import StateDefinition, CreateState
    #
    # new_state = StateDefinition(state_id="STATE_NEW_EXAMPLE")
    #
    # # Add a create_state block
    # create_state = CreateState(
    #     country="USA",
    #     owned_provinces=["x123456", "x789ABC", "xDEF012"]
    # )
    # new_state.create_states.append(create_state)
    #
    # # Add homelands
    # new_state.homelands.extend(["yankee", "dixie"])
    #
    # # Add to states file
    # states.states.append(new_state)
    #
    # # Write the modified file
    # # write_states_file(states, "00_states_modified.txt")
    # print(states_to_string(states))
    #
    # print("State file written successfully!")