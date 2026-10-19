# ChartRecorder development guidance
- The authoritative development standards are maintained at https://github.com/yuki746289/product_agent_rules (latest version: v13).
- Before changing the code, check the complete current rule set, including common rules, app rules, and any applicable project-specific coding standard.
- The local .rules directory must be fully synchronized before treating the rule setup as complete.
- Keep changes on develop; never commit to release_* branches. Keep release_0.1.0 unchanged.
- Do not change Saxo credentials, trading functionality, or the independent economic-events policy as part of configurable chart settings.
- Validate changes using the offline pytest suite and the Windows build checks.
