from dataclasses import dataclass

ALLOWED_ACTIONS = {
    "ADD_INSTANCE",
    "REMOVE_INSTANCE",
    "INCREASE_CPU",
    "DECREASE_CPU",
    "REALLOCATE_RESOURCE",
    "PRIORITIZE_WORKLOAD",
    "DO_NOTHING",
}
MAX_INSTANCES = 10
MIN_INSTANCES = 1
MAX_SCALE_STEP = 2
COOLDOWN_SECONDS = 60
CRITICAL_WORKLOADS = {"critical", "database", "payment"}


@dataclass
class SafetyResult:
    approved: bool
    reason: str


def validate(
    action: dict,
    current_instances: int,
    last_action_time=None,
    now=None,
    critical=False,
) -> SafetyResult:
    name = action.get("action")
    if name not in ALLOWED_ACTIONS:
        return SafetyResult(False, "Unknown action is not permitted.")

    raw_delta = action.get("delta", 0)
    try:
        delta = int(raw_delta or 0)
        if float(raw_delta or 0) != delta:
            raise ValueError("Scaling delta must be an integer.")
    except (TypeError, ValueError, OverflowError):
        return SafetyResult(False, "Scaling delta must be a valid integer.")

    if abs(delta) > MAX_SCALE_STEP:
        return SafetyResult(
            False,
            f"Scale step exceeds MAX_SCALE_STEP={MAX_SCALE_STEP}.",
        )

    if name in {"ADD_INSTANCE", "REMOVE_INSTANCE"} and delta < 0:
        return SafetyResult(False, "Scaling delta cannot be negative.")

    if name not in {"ADD_INSTANCE", "REMOVE_INSTANCE"} and delta != 0:
        return SafetyResult(False, "This action does not accept an instance delta.")

    if current_instances < MIN_INSTANCES or current_instances > MAX_INSTANCES:
        return SafetyResult(False, "Current instance count is outside policy limits.")

    if name == "ADD_INSTANCE":
        if current_instances + max(delta, 1) > MAX_INSTANCES:
            return SafetyResult(
                False,
                "Requested action exceeds maximum allowed resource limit.",
            )

    if name == "REMOVE_INSTANCE":
        remove = max(delta, 1)
        if current_instances - remove < MIN_INSTANCES:
            return SafetyResult(
                False,
                "Requested action would violate minimum instance limit.",
            )
        if critical:
            return SafetyResult(False, "Critical workloads cannot be removed.")

    if (
        name in {"ADD_INSTANCE", "REMOVE_INSTANCE"}
        and last_action_time is not None
        and now is not None
    ):
        try:
            elapsed = (now - last_action_time).total_seconds()
        except (TypeError, AttributeError):
            return SafetyResult(False, "Invalid cooldown timestamp.")
        if elapsed < COOLDOWN_SECONDS:
            return SafetyResult(
                False,
                "Cooldown prevents repeated scaling too quickly.",
            )

    return SafetyResult(
        True,
        "Action satisfies deterministic safety policies.",
    )
