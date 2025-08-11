package main

import (
	"context"
	"flag"
	"log"
	"os"

	"github.com/ThinkInAIXYZ/go-mcp/client"
	"github.com/ThinkInAIXYZ/go-mcp/transport"
)

func main() {
	// Define command-line flag for the MCP URL
	var mcpURL string
	flag.StringVar(&mcpURL, "url", "https://mcp-td1.swormlab.com/sse", "MCP server URL")
	flag.Parse()

	// Log which URL we're connecting to
	log.Printf("Connecting to MCP server: %s", mcpURL)

	// Create SSE transport client
	transportClient, err := transport.NewSSEClientTransport(mcpURL)
	if err != nil {
		log.Fatalf("Failed to create transport client: %v", err)
	}

	// Initialize MCP client
	mcpClient, err := client.NewClient(transportClient)
	if err != nil {
		log.Fatalf("Failed to create MCP client: %v", err)
	}
	defer mcpClient.Close()

	// Get available tools
	tools, err := mcpClient.ListTools(context.Background())
	if err != nil {
		log.Fatalf("Failed to list tools: %v", err)
	}

	// Set up a custom logger without timestamps
	logger := log.New(os.Stdout, "", 0)

	for _, tool := range tools.Tools {
		logger.Printf("Name: %s Description: %s\n", tool.Name, tool.Description)
	}
}
