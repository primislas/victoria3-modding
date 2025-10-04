import os
from pathlib import Path
from typing import TextIO
from clausewitz.victoria3.parsers.pop_parser import PopFile
from clausewitz.victoria3.model import PopState, RegionState, PopEntry


class PopWriter:
    """Writer for population configuration files"""

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

    def _write_pop_entry(self, f: TextIO, pop: PopEntry, indent_level: int):
        """Write a create_pop block"""
        indent = self._indent(indent_level)

        f.write(f"{indent}create_pop = {{\n")

        # Write properties in the correct order: pop_type, culture, religion, size
        if pop.pop_type:
            f.write(f"{self._indent(indent_level + 1)}pop_type = {pop.pop_type}\n")

        if pop.culture:
            f.write(f"{self._indent(indent_level + 1)}culture = {pop.culture}\n")

        if pop.religion:
            f.write(f"{self._indent(indent_level + 1)}religion = {pop.religion}\n")

        if pop.size is not None:
            f.write(f"{self._indent(indent_level + 1)}size = {pop.size}\n")

        f.write(f"{indent}}}\n")

    def _write_region_state(self, f: TextIO, region_state: RegionState, indent_level: int):
        """Write a region_state block"""
        indent = self._indent(indent_level)

        f.write(f"{indent}region_state:{region_state.country_tag} = {{\n")

        # Write all create_pop blocks
        for pop in region_state.populations:
            self._write_pop_entry(f, pop, indent_level + 1)

        f.write(f"{indent}}}\n")

    def _write_state(self, f: TextIO, state: PopState, indent_level: int):
        """Write a state definition"""
        indent = self._indent(indent_level)

        f.write(f"{indent}s:{state.state_id} = {{\n")

        # Write all region_state blocks
        for region_state in state.region_states:
            self._write_region_state(f, region_state, indent_level + 1)

        f.write(f"{indent}}}\n")

    def write_to_file(self, pops_file: PopFile, file_path: str | Path):
        """
        Write a PopsFile to a file

        Args:
            pops_file: PopsFile object to write
            file_path: Path to the output file
        """
        for state in pops_file.states:
            state.merge_pops()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            self.write_to_stream(pops_file, f)

    def write_to_stream(self, pops_file: PopFile, f: TextIO):
        """
        Write a PopsFile to a stream

        Args:
            pops_file: PopsFile object to write
            f: File stream to write to
        """
        # Write opening
        f.write("POPS = {\n")

        # Write each state
        for state in pops_file.states:
            self._write_state(f, state, indent_level=1)

        # Write closing
        f.write("}\n")

    def write_to_string(self, pops_file: PopFile) -> str:
        """
        Write a PopsFile to a string

        Args:
            pops_file: PopsFile object to write

        Returns:
            String representation of the file
        """
        from io import StringIO

        stream = StringIO()
        self.write_to_stream(pops_file, stream)
        return stream.getvalue()


def write_pops_file(pops_file: PopFile, file_path: str | Path,
                    indent_size: int = 1, use_tabs: bool = True):
    """
    Convenience function to write a pops file

    Args:
        pops_file: PopsFile object to write
        file_path: Path to the output file
        indent_size: Number of spaces/tabs per indent level
        use_tabs: Whether to use tabs (True) or spaces (False)
    """
    writer = PopWriter(indent_size=indent_size, use_tabs=use_tabs)
    writer.write_to_file(pops_file, file_path)


def pops_to_string(pops_file: PopFile, indent_size: int = 1,
                   use_tabs: bool = True) -> str:
    """
    Convenience function to convert a PopsFile to a string

    Args:
        pops_file: PopsFile object to write
        indent_size: Number of spaces/tabs per indent level
        use_tabs: Whether to use tabs (True) or spaces (False)

    Returns:
        String representation of the file
    """
    writer = PopWriter(indent_size=indent_size, use_tabs=use_tabs)
    return writer.write_to_string(pops_file)


# Example usage
if __name__ == "__main__":
    from clausewitz.victoria3.parsers.pop_parser import parse_pop_file
    from clausewitz.victoria3.model import PopState, RegionState, PopEntry

    # Parse an existing file
    pops = parse_pop_file("../../../nations_released/game/common/history/pops/05_north_america.txt")

    # Write it back out
    # write_pops_file(pops, "05_north_america_output.txt")

    # Or get as string
    output_str = pops_to_string(pops)
    print(output_str)

    # Example: Create a new state programmatically
    # new_state = State(state_id="STATE_NEW_EXAMPLE")
    #
    # # Add a region_state block
    # region = RegionState(country_tag="USA")
    #
    # # Add population entries
    # pop1 = PopEntry(
    #     culture="yankee",
    #     size=10000
    # )
    # region.populations.append(pop1)
    #
    # pop2 = PopEntry(
    #     pop_type="slaves",
    #     culture="afro_american",
    #     size=5000
    # )
    # region.populations.append(pop2)
    #
    # pop3 = PopEntry(
    #     culture="irish",
    #     religion="catholic",
    #     size=3000
    # )
    # region.populations.append(pop3)
    #
    # new_state.region_states.append(region)
    #
    # # Add to pops file
    # pops.states.append(new_state)
    #
    # # Write the modified file
    # # write_pops_file(pops, "05_north_america_modified.txt")
    #
    # # Preview a single state
    # single_state = pops.get_state("STATE_NEW_YORK")
    # if single_state:
    #     single_file = PopsFile()
    #     single_file.states.append(single_state)
    #     print("\nPreview of STATE_NEW_YORK:")
    #     print(pops_to_string(single_file))
    #
    # print("\nPops file written successfully!")