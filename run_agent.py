def run_agent(task_override=None):
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()

    final_task = task_override if task_override else task

    async def agent_runner():
        print("[DEBUG] Running agent with task:", final_task)
        agent = Agent(
            browser_context=context,
            task=final_task,
            llm=llm,
        )
        print("[DEBUG] Agent initialized. Running task...")
        result = await agent.run()

        # Extract only the final message
        if isinstance(result, dict) and "message" in result:
            return result["message"]
        elif hasattr(result, "message"):
            return result.message
        elif hasattr(result, "content"):
            return result.content
        else:
            return str(result)

    return asyncio.run(agent_runner())
