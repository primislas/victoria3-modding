import logging
import os
import re
from pathlib import Path

from clausewitz.victoria3.model import PopState, StateDefinition, PopEntry, RegionState
from clausewitz.victoria3.parsers.pop_parser import parse_pop_file, PopFile
from clausewitz.victoria3.parsers.state_parser import parse_states_file, StatesFile
from clausewitz.victoria3.writers.pop_writer import PopWriter
from clausewitz.victoria3.writers.state_writer import StateWriter

primary_tags = {
    "quechua": "TWT",
    "platinean": "ARG",
    "patagonian": "PAT",
    "guarani": "GRI",
    "mongol": "MGL",
    "khmer": "CAM",
    "burmese": "BUR",
    "polish": "POL",
    # "british": "ENG",
    "greek": "GRE",
}

primary_state_tags = {
    "british": {
        "SOUTH_ATLANTIC_ISLANDS": "PRG"
    },
    "sulista": {
        "STATE_SANTA_CATARINA": "CTR",
        "STATE_RIO_GRANDE_DO_SUL": "PNI",
    },
    "romanian": {
        "STATE_BESSARABIA": "MOL",
    },
    "ukrainian": {
        "STATE_DOBRUDJA": "MOL",
    },
    "north_german": {
        "STATE_UPPER_SILESIA": "BOH",
        "STATE_RHINELAND": "RHE",
        # "STATE_WESTPHALIA": "WES",
        # "STATE_RUHR": "WES",
    },
    "alemannic": {
        "STATE_ALSACE_LORRAINE": "RHE",
    },
    "north_italian": {
        "STATE_LOMBARDY": "LOM",
        "STATE_SOUTH_TYROL": "LOM",
    },
    "russian": {
        "STATE_ROSTOV": "DON",
        "STATE_STAVROPOL": "DON",
        "STATE_TARTARIA": "DON",
        "STATE_SAMARA": "DON",
        "STATE_ASTRAKHAN": "DON",

        "STATE_TOMSK": "URL",
        "STATE_TOBOLSK": "URL",
        "STATE_CHELYABINSK": "URL",

        "STATE_KRASNOYARSK": "TNS",
        "STATE_UPPER_YENISEYSK": "TNS",
        "STATE_IRKUTSK": "TNS",
        "STATE_OUTER_MANCHURIA": "TNS",
    },
    "azerbaijani": {
        "STATE_KARS": "ARM",
    },
    "serb": {
        "STATE_BOSNIA": "BOS",
        "STATE_EASTERN_SERBIA": "SER",
    },
    "mashriqi": {
        "STATE_ALEPPO": "SYR",
        "STATE_DEIR_EZ_ZOR": "IRQ",
        "STATE_BASRA": "IRQ",
    },
    "bedouin": {
        "STATE_TRANSJORDAN": "EOT",
    },
    "kazak": {
        "STATE_JETISY": "OZH",
    },
    "siberian": {
        "STATE_AMUR": "MCH",
        "STATE_OUTER_MANCHURIA": "MCH",
    },
    "han": {
        "STATE_SHENGJING": "MCH",
        "STATE_YUNNAN": "YUN",
        "STATE_GUANGXI": "GNG",
        "STATE_NINGXIA": "XIB",
    },
    "tibetan": {
        "STATE_QINGHAI": "TIB",
    },
    "nordestino": {
        "STATE_BAHIA": "BHI",
    },
}

state_culture_assignments = {
    "STATE_KAZAN": {
        "tag": "TAR",
        "culture": "tatar",
    },
    "STATE_NENETSIA": {
        "tag": "KNT",
        "culture": "ugrian",
    },
    "STATE_OB": {
        "tag": "KNT",
        "culture": "ugrian",
    },
    "STATE_PERM": {
        "tag": "PRM",
        "culture": "ugrian",
    },
    "STATE_GALICH": {
        "tag": "PRM",
        "culture": "ugrian",
    },
    "STATE_ARKHANGELSK": {
        "tag": "PRM",
        "culture": "ugrian",
    },
    "STATE_EAST_KARELIA": {
        "tag": "KRL",
        "culture": "karelian",
    },
    "STATE_KOLA": {
        "tag": "SMI",
        "culture": "sami",
    },
    "STATE_VYATKA": {
        "tag": "UDM",
        "culture": "udmurt",
    },
    "STATE_TAMBOV": {
        "tag": "MRD",
        "culture": "mordvin",
    },
    "STATE_OKHOTSK": {
        "tag": "YAK",
        "culture": "yakut",
    },
    "STATE_CHITA": {
        "tag": "BRY",
        "culture": "buryat",
    },
    "STATE_IRKUTSK": {
        "tag": "BRY",
        "culture": "buryat",
    },
    "STATE_AMUR": {
        "tag": "BRY",
        "culture": "buryat",
    },
    "STATE_TRANS_BAIKAL": {
        "tag": "BRY",
        "culture": "buryat",
    },
    "STATE_DZUNGARIA": {
        "tag": "XIN",
        "culture": "uighur",
    },
    "STATE_GANSU": {
        "tag": "MGL",
        "culture": "mongol",
    },

}


# Simple colorizer for console logs
class _ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",    # Cyan
        logging.INFO: "\033[32m",     # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",    # Red
        logging.CRITICAL: "\033[41m", # Red background
    }
    RESET = "\033[0m"

    def __init__(self, fmt: str, use_color: bool = True):
        super().__init__(fmt)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        if self.use_color:
            color = self.COLORS.get(record.levelno)
            if color:
                return f"{color}{msg}{self.RESET}"
        return msg

def _setup_logging(level_str: str) -> logging.Logger:
    logger = logging.getLogger("mirror_dir")
    if logger.handlers:
        return logger  # already configured (avoid duplicate handlers)
    level = getattr(logging, level_str.upper(), logging.INFO)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    fmt = "[%(asctime)s][%(levelname)s] %(message)s"
    handler.setFormatter(_ColorFormatter(fmt=fmt, use_color=True))
    logger.addHandler(handler)
    return logger

logger = _setup_logging("DEBUG")


# countries
tag_pattern = re.compile(r'^([A-Z]{3})\s*=\s*\{')
cultures_pattern = re.compile(r'cultures\s*=\s*\{\s*([^}]+)\s*\}')
capital_pattern = re.compile(r'capital\s*=\s*([A-Z_]+)')
# states
state_id_pattern = re.compile(r's:([A-Z_]+)\s*=\s*\{')
create_state_pattern = re.compile(r'create_state\s*=\s*\{')
country_pattern = re.compile(r'country\s*=\s*c:([A-Z]{3})\s*')
owned_provinces_pattern = re.compile(r'owned_provinces\s*=\s*\{\s*([^}]+)\s*\}')
add_homeland_pattern = re.compile(r'add_homeland\s*=\s*cu:([a-z]+)\s*')
add_claim_pattern = re.compile(r'add_claim\s*=\s*c:([A-Z]{3})\s*')
# pops
region_state_pattern = re.compile(r'region_state:([A-Z]{3})\s*=\s*{')
create_pop_pattern = re.compile(r'create_pop\s*=\s*\{')
culture_pattern = re.compile(r'culture\s*=\s*([a-z]+)\s*')
religion_pattern = re.compile(r'religion\s*=\s*([a-z]+)\s*')
size_pattern = re.compile(r'size\s*=\s*(\d+)\s*')


class Country:
    id: str
    cultures: list[str]
    dynamic_country_definition: bool = False
    capital: str | None = None

    def __init__(self, tag_id: str, cultures: list[str] | None = None):
        self.id = tag_id
        self.cultures = cultures if cultures is not None else []

    def __str__(self):
        return f"Country(\"{self.id}\")"

    def __repr__(self):
        return f"Country(\"{self.id}\")"


def main(game_dir: str, mod_dir: str):
    game_path, mod_path = validate_dirs(game_dir, mod_dir)
    countries = parse_countries(game_path)
    logger.info(f"Parsed {len(countries)} non-dynamic countries")

    states = parse_states(game_path)
    state_ids = set([s.state_id for s in states])
    logger.info(f"Parsed {len(state_ids)} unique states and {len(states)} owned states")

    pops = parse_pops(game_path)
    logger.info(f"Parsed {len(pops)} pops")

    identify_occupied_states(countries, states, pops)
    write_out(mod_path, states, pops)


def validate_dirs(game_dir: str, mod_dir: str) -> tuple[Path, Path]:
    if not game_dir:
        raise ValueError("Game dir must be specified")
    if not mod_dir:
        raise ValueError("Mod dir must be specified")
    if not os.path.isdir(game_dir):
        raise ValueError(f"Game dir '{game_dir}' does not exist or is not a directory")
    if not os.path.isdir(mod_dir):
        raise ValueError(f"Mod dir '{mod_dir}' does not exist or is not a directory")
    return Path(game_dir).resolve(), Path(mod_dir).resolve()


def parse_countries(game_path: Path) -> list[Country]:
    tag_dir = game_path / "game" / "common" / "country_definitions"
    tags: list[Country] = []

    for f in os.listdir(tag_dir):
        logger.info(f"Parsing tag file: {f}")

        file_path = tag_dir / f
        if not file_path.is_file():
            logger.warning(f"Skipping non-file: {file_path}")
            continue

        # Read file to list of strings
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        current_tag: Country | None = None

        for line in lines:
            # Detect new tag (e.g., "JAN = {")
            tag_match = tag_pattern.match(line.strip())
            if tag_match:
                tag_id = tag_match.group(1)
                logger.debug(f"Parsing tag: {tag_id}")
                if current_tag and not current_tag.dynamic_country_definition:
                    tags.append(current_tag)
                current_tag = Country(tag_id)
                continue

            if not current_tag:
                continue

            if "dynamic_country_definition = yes" in line:
                current_tag.dynamic_country_definition = True
                continue

            # Detect cultures definition
            if cultures_match := cultures_pattern.search(line):
                # Extract culture values (split by whitespace)
                cultures_str = cultures_match.group(1)
                cultures = [c.strip() for c in cultures_str.split() if c.strip()]
                current_tag.cultures = cultures
                logger.debug(f"Parsing cultures for {current_tag.id}: {cultures}")
                continue

            if capital_match := capital_pattern.search(line):
                capital_state_id = capital_match.group(1)
                current_tag.capital = capital_state_id
                continue
        else:
            if current_tag and not current_tag.dynamic_country_definition:
                tags.append(current_tag)

    return tags


def parse_states(game_path: Path) -> list[StateDefinition]:
    state_dir = game_path / "game" / "common" / "history" / "states"
    states: list[StateDefinition] = []

    for f in os.listdir(state_dir):
        file_path = state_dir / f
        if not file_path.is_file():
            logger.warning(f"Skipping non-file: {file_path}")
            continue
        logger.info(f"Parsing state file: {f}")

        state_file = parse_states_file(file_path)
        states.extend(state_file.states)

    return states


def parse_pops(game_path: Path) -> list[PopFile]:
    pop_dir = game_path / "game" / "common" / "history" / "pops"
    pop_files: list[PopFile] = []

    for f in os.listdir(pop_dir):
        file_path = pop_dir / f
        if not file_path.is_file():
            logger.warning(f"Skipping non-file: {file_path}")
            continue
        logger.info(f"Parsing pop file: {f}")

        pop_file = parse_pop_file(file_path)
        pop_files.append(pop_file)

    return pop_files


def identify_occupied_states(countries: list[Country], states: list[StateDefinition], pop_files: list[PopFile]):
    states_by_id = {}
    for state in states:
        ss = states_by_id.get(state.state_id, [])
        ss.append(state)
        states_by_id[state.state_id] = ss

    countries_by_id = {}
    for country in countries:
        countries_by_id[country.id] = country

    pop_states: list[PopState] = [pop_state for pop_file in pop_files for pop_state in pop_file.states]
    pops_by_state_id = {}
    for pop_state in pop_states:
        state_regions = pops_by_state_id.get(pop_state.state_id, [])
        state_regions.extend(pop_state.region_states)
        pops_by_state_id[pop_state.state_id] = state_regions

    for state_id, state_regions in pops_by_state_id.items():
        if state_id in state_culture_assignments:
            reassign_state_and_culture(state_id, states_by_id, state_regions)
            continue

        pops_by_country_id: dict[str, list[PopEntry]] = {}
        for region in state_regions:
            country_pops: list[PopEntry] = pops_by_country_id.get(region.country_tag, [])
            country_pops.extend(region.populations)
            pops_by_country_id[region.country_tag] = country_pops

        for country_id, country_pops in pops_by_country_id.items():
            dominant_culture = identify_dominant_culture(country_pops)
            country = countries_by_id.get(country_id)
            nation_state = None
            warnings = []
            if country:
                states_with_dominant_culture = [c for c in countries if dominant_culture in c.cultures]
                if len(states_with_dominant_culture) == 1:
                    nation_state = states_with_dominant_culture[0]
                elif len(states_with_dominant_culture) > 1:
                    nation_states = [c for c in states_with_dominant_culture if len(c.cultures) == 1]
                    if len(nation_states) > 1:
                        # if country in nation_states:
                        #     nation_state = nation_states[0]
                        # else:
                        state_capital = [n for n in nation_states if n.capital == state_id]
                        if len(state_capital) == 1:
                            nation_state = state_capital[0]
                            if country_id != nation_state.id:
                                warnings.append(f"Assigning capital state {dominant_culture} in {state_id}: {country_id} -> {nation_state.id}")
                        else:
                            warnings.append(f"Found multiple nation states for {dominant_culture} in {state_id} / {country_id}: {nation_states}")
                    elif len(nation_states) == 1:
                        nation_state = nation_states[0]
                    else:
                        warnings.append(f"Found multiple nation states for {dominant_culture} in {state_id} / {country_id}: {states_with_dominant_culture}")
                else:
                    warnings.append(f"Could not find nation state for {dominant_culture} in {state_id} / {country_id}")
            else:
                warnings.append(f"Could not find country definition for {country_id} in state {state_id}")

            if not nation_state:
                primary_tag = primary_tags.get(dominant_culture)
                if not primary_tag:
                    primary_tag = primary_state_tags.get(dominant_culture, {}).get(state_id)
                if primary_tag and primary_tag != country_id:
                    logger.debug(f"Assigning primary tag {dominant_culture} in {state_id}: {country_id} -> {primary_tag}")
                    nation_state = countries_by_id.get(primary_tag)

            if not nation_state:
                for warning in warnings:
                    logger.warning(warning)
            elif nation_state.id != country_id:
                logger.info(f"Identified occupied state for {dominant_culture} in {state_id}: {country_id} -> {nation_state.id}")
                for region in state_regions:
                    if region.country_tag == country_id:
                        region.country_tag = nation_state.id
                for state in states_by_id.get(state_id, []):
                    for state_region in state.create_states:
                        if state_region.country == country_id:
                            state_region.country = nation_state.id
            else:
                logger.debug(f"No change for {dominant_culture} in {state_id}: {country_id}")


def identify_dominant_culture(pops: list[PopEntry]) -> str:
    pop_size_by_culture: dict[str, int] = {}
    for pop in pops:
        pop_size_by_culture[pop.culture] = pop_size_by_culture.get(pop.culture, 0) + pop.size
    culture_sizes = list(pop_size_by_culture.items())
    culture_sizes.sort(key=lambda x: x[1], reverse=True)
    dominant_culture = culture_sizes[0]
    return dominant_culture[0]


def identify_primary_country(state_id: str, owner_country_id, dominant_culture: str, countries: list[Country]) -> tuple[Country | None, list[str]]:
    nation_state: Country | None = None
    warnings = []
    states_with_dominant_culture = [c for c in countries if dominant_culture in c.cultures]
    if len(states_with_dominant_culture) == 1:
        nation_state = states_with_dominant_culture[0]
    elif len(states_with_dominant_culture) > 1:
        nation_states = [c for c in states_with_dominant_culture if len(c.cultures) == 1]
        if len(nation_states) > 1:
            # if country in nation_states:
            #     nation_state = nation_states[0]
            # else:
            state_capital = [n for n in nation_states if n.capital == state_id]
            if len(state_capital) == 1:
                nation_state = state_capital[0]
                if owner_country_id != nation_state.id:
                    warnings.append(f"Assigning capital state {dominant_culture} in {state_id}: {owner_country_id} -> {nation_state.id}")
            else:
                warnings.append(f"Found multiple nation states for {dominant_culture} in {state_id} / {owner_country_id}: {nation_states}")
        elif len(nation_states) == 1:
            nation_state = nation_states[0]
        else:
            warnings.append(f"Found multiple nation states for {dominant_culture} in {state_id} / {owner_country_id}: {states_with_dominant_culture}")
    else:
        warnings.append(f"Could not find nation state for {dominant_culture} in {state_id} / {owner_country_id}")

    return nation_state, warnings


def reassign_state_and_culture(state_id: str, states_by_id: dict[str, list[StateDefinition]], state_regions: list[RegionState]):
    tag = state_culture_assignments[state_id]["tag"]
    culture = state_culture_assignments[state_id]["culture"]
    logger.debug(f"Assigning {culture} {state_id} -> {tag}")

    for state in  states_by_id.get(state_id, []):
        for create_state in state.create_states:
            create_state.country = tag

    for region in state_regions:
        region.country_tag = tag
        largest_pop: PopEntry | None = None
        for pop in region.populations:
            if not largest_pop:
                largest_pop = pop
            elif pop.size > largest_pop.size:
                largest_pop = pop
        if largest_pop:
            largest_pop.culture = culture

def write_out(mod_path: Path, states: list[StateDefinition], pops: list[PopFile]):
    state_dir = mod_path / "common" / "history" / "states"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file_path = state_dir / "00_states.txt"
    states_file = StatesFile(states)
    logger.info(f"Writing state file: {state_file_path}")
    StateWriter().write_to_file(states_file, state_file_path)

    pop_dir = mod_path / "common" / "history" / "pops"
    for pop_file in pops:
        pop_file_path = pop_dir / pop_file.filename
        logger.info(f"Writing pop file: {pop_file_path}")
        PopWriter().write_to_file(pop_file, pop_file_path)

def cleanup_line(text: str) -> str:
    return re.sub(r'#.*$', '', text, flags=re.MULTILINE).strip()


if __name__ == "__main__":
    _setup_logging("DEBUG")
    _game_dir = "/home/primislas/.steam/debian-installation/steamapps/common/Victoria 3"
    _mod_dir = Path("./nations_released").resolve()
    main(_game_dir, str(_mod_dir))
