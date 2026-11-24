type OpenAITool = {
  type: "function";
  function: {
    name: string;
    description?: string;
    parameters?: Record<string, unknown>;
  };
};

type MCPTool = {
  name: string;
  description?: string;
  inputSchema: Record<string, unknown>;
};

class ToolRegistry {
  private tools: OpenAITool[] = [];
  private localToolNames = new Set<string>();
  private mcpToolNames = new Set<string>();

  constructor(localToolNames: string[]) {
    this.localToolNames = new Set(localToolNames);
  }

  registerMcpTools(mcpTools: MCPTool[]): void {
    const existingNames = new Set(
      this.tools
        .filter(tool => tool.type === "function")
        .map(tool => tool.function.name)
    );

    const seenNames = new Set<string>();
    const duplicateNames = new Set<string>();

    for (const tool of mcpTools) {
      if (seenNames.has(tool.name)) {
        duplicateNames.add(tool.name);
      }

      seenNames.add(tool.name);
    }

    const conflicts = new Set(
      [...seenNames].filter(
        name =>
          existingNames.has(name) ||
          this.localToolNames.has(name) ||
          this.mcpToolNames.has(name)
      )
    );

    if (duplicateNames.size > 0 || conflicts.size > 0) {
      const details: string[] = [];

      if (duplicateNames.size > 0) {
        details.push(
          `MCP 内部重复: ${[...duplicateNames].join(", ")}`
        );
      }

      if (conflicts.size > 0) {
        details.push(
          `与已有工具重名: ${[...conflicts].join(", ")}`
        );
      }

      throw new Error(
        `MCP 工具注册失败，工具名称必须唯一；${details.join("；")}`
      );
    }

    const openaiTools: OpenAITool[] = mcpTools.map(tool => ({
      type: "function",
      function: {
        name: tool.name,
        description: tool.description ?? "",
        parameters: tool.inputSchema,
      },
    }));

    this.tools.push(...openaiTools);

    for (const tool of mcpTools) {
      this.mcpToolNames.add(tool.name);
    }
  }
}


const registry = new ToolRegistry([
  "get_current_time",
]);

registry.registerMcpTools([
  {
    name: "get_current_time",
    description: "获取当前时间",
    inputSchema: {},
  },
]);