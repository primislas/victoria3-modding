from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class CreateState:
    """Represents a create_state block within a state definition"""
    country: str
    owned_provinces: List[str] = field(default_factory=list)
    state_type: Optional[str] = None

    def __repr__(self):
        type_str = f", state_type={self.state_type}" if self.state_type else ""
        return f"CreateState(country={self.country}, provinces={len(self.owned_provinces)}{type_str})"


@dataclass
class StateDefinition:
    """Represents a state definition"""
    state_id: str
    create_states: List[CreateState] = field(default_factory=list)
    homelands: List[str] = field(default_factory=list)
    claims: List[str] = field(default_factory=list)

    def get_total_provinces(self) -> int:
        """Get total number of provinces across all create_state blocks"""
        return sum(len(cs.owned_provinces) for cs in self.create_states)

    def get_countries(self) -> List[str]:
        """Get list of countries that own parts of this state"""
        return [cs.country for cs in self.create_states]

    def merge_states(self) -> "StateDefinition":
        states_by_country = {}
        for cs in self.create_states:
            states = states_by_country.get(cs.country, [])
            states.append(cs)
            states_by_country[cs.country] = states
        if len(states_by_country) == len(self.create_states):
            return self

        create_states = []
        for cs in self.create_states:
            states = states_by_country.pop(cs.country, [])
            if len(states) == 1:
                create_states.append(states[0])
            elif len(states) > 1:
                merged = CreateState(cs.country)
                for state in states:
                    merged.owned_provinces.extend(state.owned_provinces)
                if all([state.state_type for state in states]):
                    merged.state_type = states[0].state_type
                create_states.append(merged)
        self.create_states = create_states
        return self

    def __repr__(self):
        return f"StateDefinition(state_id={self.state_id}, create_states={len(self.create_states)}, homelands={len(self.homelands)}, claims={len(self.claims)})"


@dataclass
class PopEntry:
    """Represents a single population entry"""
    culture: Optional[str] = None
    religion: Optional[str] = None
    size: Optional[int] = None
    pop_type: Optional[str] = None

    def __repr__(self):
        parts = []
        if self.pop_type:
            parts.append(f"pop_type={self.pop_type}")
        if self.culture:
            parts.append(f"culture={self.culture}")
        if self.religion:
            parts.append(f"religion={self.religion}")
        if self.size:
            parts.append(f"size={self.size}")
        return f"PopEntry({', '.join(parts)})"


@dataclass
class RegionState:
    """Represents a region_state block"""
    country_tag: str
    populations: List[PopEntry] = field(default_factory=list)

    def __repr__(self):
        return f"RegionState(country_tag={self.country_tag}, populations={len(self.populations)})"

    def merge_pops(self) -> "RegionState":
        if not self.populations:
            return self

        merged_pops = []
        seen_keys = {}  # Maps (culture, religion, pop_type) -> index in merged_pops

        for pop in self.populations:
            # Create a key tuple for identifying identical pops
            key = (pop.culture, pop.religion, pop.pop_type)

            if key in seen_keys:
                # Found a duplicate - add size to existing entry
                index = seen_keys[key]
                if merged_pops[index].size is not None and pop.size is not None:
                    merged_pops[index].size += pop.size
                elif pop.size is not None:
                    merged_pops[index].size = pop.size
            else:
                # First occurrence - add to merged list
                seen_keys[key] = len(merged_pops)
                # Create a new PopEntry to avoid modifying the original
                merged_pop = PopEntry(
                    culture=pop.culture,
                    religion=pop.religion,
                    size=pop.size,
                    pop_type=pop.pop_type
                )
                merged_pops.append(merged_pop)

        self.populations = merged_pops
        return self


@dataclass
class PopState:
    """Represents a state block"""
    state_id: str
    region_states: List[RegionState] = field(default_factory=list)

    def __repr__(self):
        return f"State(state_id={self.state_id}, region_states={len(self.region_states)})"

    def merge_pops(self) -> "PopState":
        region_states_by_country = {}
        for region_state in self.region_states:
            states = region_states_by_country.get(region_state.country_tag, [])
            states.append(region_state)
            region_states_by_country[region_state.country_tag] = states
        if len(region_states_by_country) == len(self.region_states):
            for region_state in self.region_states:
                region_state.merge_pops()
            return self

        region_states = []
        for region_state in self.region_states:
            states = region_states_by_country.pop(region_state.country_tag, [])
            if len(states) == 1:
                region_states.append(states[0])
            elif len(states) > 1:
                merged = RegionState(region_state.country_tag)
                for state in states:
                    merged.populations.extend(state.populations)
                region_states.append(merged)
        self.region_states = region_states

        for region_state in self.region_states:
            region_state.merge_pops()
        return self
