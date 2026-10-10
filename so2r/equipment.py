"""Equipment effects that stack across equipped items (options: Equipment group), sent as slot_data.equipment."""
from typing import Optional

# option name -> (SpecialEffects ids, {effect id: cap}).
# SpecialEffects ids; the game sums 23-27,30,32,36,38,41,44,104 already; flags/chance/weapon-only effects never stack
# (docs/EQUIPMENT_STACKING.md)
EQUIPMENT_STACK_GROUPS = {
    "stack_extra_attacks": ([68], {}),  # cap comes from extra_attack_cap
    "stack_regeneration": ([8, 15, 16], {15: 100}),
    "stack_spell_power": ([89, 90, 91, 92], {}),
    "stack_cost_cuts": ([17, 86, 87, 270], {17: 90, 86: 90, 87: 10, 270: 90}),
    "stack_damage_cuts": ([94, 100], {94: 80, 100: 75}),
}
EXTRA_ATTACK_EFFECT = 68


def equipment_slot_data(options) -> Optional[dict]:
    toggles = {name: getattr(options, name, None) for name in EQUIPMENT_STACK_GROUPS}
    cap = getattr(options, "extra_attack_cap", None)
    # Absent on the tests' hand-built option namespaces.
    if any(option is None for option in toggles.values()) or cap is None:
        return None
    ids = set()
    caps = {}
    for name, (effects, group_caps) in EQUIPMENT_STACK_GROUPS.items():
        if not toggles[name].value:
            continue
        ids.update(effects)
        caps.update(group_caps)
    if EXTRA_ATTACK_EFFECT in ids:
        caps[EXTRA_ATTACK_EFFECT] = cap.value
    return {"version": 1, "stack": sorted(ids), "caps": {str(k): caps[k] for k in sorted(caps)}}
