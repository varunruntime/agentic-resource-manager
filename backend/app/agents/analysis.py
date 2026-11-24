class AnalysisAgent:
    def analyze(self, obs):
        cpu = float(obs.get("cpu_percent", 0))
        memory = float(obs.get("memory_percent", 0))
        network = float(obs.get("network_usage", 0))

        issues = []

        if cpu >= 80:
            issues.append("OVERLOAD")

        if memory >= 90:
            issues.append("MEMORY_PRESSURE")

        if cpu < 30 and cpu >= 0:
            issues.append("UNDERUTILIZATION")

        if network > 85:
            issues.append("NETWORK_BOTTLENECK")

        if not issues:
            issues.append("NORMAL")

        severity = "HIGH" if (
            "OVERLOAD" in issues or
            "MEMORY_PRESSURE" in issues
        ) else "MEDIUM" if len(issues) > 1 or issues[0] != "NORMAL" else "LOW"

        return {
            "issue": issues,
            "severity": severity,
            "reason": (
                f"Current CPU={cpu:.1f}%, "
                f"Memory={memory:.1f}%, "
                f"Network={network:.1f}%."
            )
        }