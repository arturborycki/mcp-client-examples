import argparse
import logging
import sys
from functools import partial
from urllib.parse import urlparse
from collections.abc import AsyncGenerator, Awaitable, Callable

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.message import SessionMessage
from mcp.shared.session import RequestResponder

if not sys.warnoptions:
    import warnings

    warnings.simplefilter("ignore")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("client")


async def message_handler(
    message: RequestResponder[types.ServerRequest, types.ClientResult] | types.ServerNotification | Exception,
) -> None:
    if isinstance(message, Exception):
        logger.error("Error: %s", message)
        return

    logger.info("Received message from server: %s", message)


async def call_tool(session, tool_name: str, tool_args: dict) -> None:
    """Call a tool using an existing session."""
    try:
        # Call the tool with the provided arguments
        logger.info(f"Executing {tool_name} with arguments: {tool_args}")
        result = await session.call_tool(tool_name, tool_args)
        
        # Display the results
        print(f"\nResults from {tool_name}:")
        
        # Handle different content types in the response
        if result.structuredContent:
            print("Structured content:")
            import json
            print(json.dumps(result.structuredContent, indent=2))
        
        for content in result.content:
            if content.type == "text":
                print(content.text)
            else:
                print(f"Content of type {content.type} received")
                
        return result
    except Exception as e:
        logger.error(f"Error calling tool: {e}")
        return None


async def run_session(
    read_stream: MemoryObjectReceiveStream[SessionMessage | Exception],
    write_stream: MemoryObjectSendStream[SessionMessage],
    client_info: types.Implementation | None = None,
    tool_to_call: str = None,
    tool_args: dict = None,
) -> None:
    async with ClientSession(
        read_stream,
        write_stream,
        message_handler=message_handler,
        client_info=client_info,
    ) as session:
        logger.info("Initializing session")
        await session.initialize()
        logger.info("Initialized")
        
        # Get the list of tools
        logger.info("Fetching available tools...")
        tools_result = await session.list_tools()
        
        # Display tool information
        print("\nAvailable tools:")
        for tool in tools_result.tools:
            print(f"- {tool.name}: {tool.description}")
        
        # If a specific tool was requested
        if tool_to_call:
            await call_tool(session, tool_to_call, tool_args)
            return
        
        # Interactive menu for using Teradata tools
        print("\nExample Teradata tools you can use:")
        print("1. Run a query (SELECT * FROM dbc.dbcinfo)")
        print("2. List negative values in a table")
        print("3. List distinct values in a column")
        print("4. Get standard deviation for a column")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == "1":
            # Run a query
            query = input("Enter your SQL query (default: SELECT * FROM dbc.dbcinfo): ") or "SELECT * FROM dbc.dbcinfo"
            await call_tool(session, "query", {"query": query})
            
        elif choice == "2":
            # List negative values
            table = input("Enter table name: ")
            await call_tool(session, "list_negative_values", {"table_name": table})
            
        elif choice == "3":
            # List distinct values
            table = input("Enter table name: ")
            await call_tool(session, "list_distinct_values", {"table_name": table})
            
        elif choice == "4":
            # Get standard deviation
            table = input("Enter table name: ")
            column = input("Enter column name: ")
            await call_tool(session, "standard_deviation", {"table_name": table, "column_name": column})
            
        elif choice != "5":
            print("Invalid choice.")

async def run_streamablehttp_session(
    read_stream: MemoryObjectReceiveStream[SessionMessage | Exception],
    write_stream: MemoryObjectSendStream[SessionMessage],
    get_session_id_callback: Callable[[], str | None],
    tool_to_call: str = None,
    tool_args: dict = None,
) -> None:
    async with ClientSession(
        read_stream,
        write_stream,
        message_handler=message_handler,
    ) as session:
        logger.info("Initializing session")
        await session.initialize()
        logger.info("Initialized")
        
        # Get the list of tools
        logger.info("Fetching available tools...")
        tools_result = await session.list_tools()
        
        # Display tool information
        print("\nAvailable tools:")
        for tool in tools_result.tools:
            print(f"- {tool.name}: {tool.description}")
        
        # If a specific tool was requested
        if tool_to_call:
            await call_tool(session, tool_to_call, tool_args)
            return
        
        # Interactive menu for using Teradata tools
        print("\nExample Teradata tools you can use:")
        print("1. Run a query (SELECT * FROM dbc.dbcinfo)")
        print("2. List negative values in a table")
        print("3. List distinct values in a column")
        print("4. Get standard deviation for a column")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == "1":
            # Run a query
            query = input("Enter your SQL query (default: SELECT * FROM dbc.dbcinfo): ") or "SELECT * FROM dbc.dbcinfo"
            await call_tool(session, "query", {"query": query})
            
        elif choice == "2":
            # List negative values
            table = input("Enter table name: ")
            await call_tool(session, "list_negative_values", {"table_name": table})
            
        elif choice == "3":
            # List distinct values
            table = input("Enter table name: ")
            await call_tool(session, "list_distinct_values", {"table_name": table})
            
        elif choice == "4":
            # Get standard deviation
            table = input("Enter table name: ")
            column = input("Enter column name: ")
            await call_tool(session, "standard_deviation", {"table_name": table, "column_name": column})
            
        elif choice != "5":
            print("Invalid choice.")


async def main(command_or_url: str, args: list[str], env: list[tuple[str, str]], tool_name: str = None, tool_args: dict = None):
    env_dict = dict(env)

    if urlparse(command_or_url).scheme in ("http", "https"):
        # Check if URL ends with /sse
        if command_or_url.endswith("/sse"):
            logger.info(f"Connecting to SSE endpoint: {command_or_url}...")
            # Use SSE client for HTTP(S) URLs ending with /sse
            async with sse_client(command_or_url) as streams:
                await run_session(*streams, tool_to_call=tool_name, tool_args=tool_args)
        else:
            # Use SSE client for other HTTP(S) URLs
            logger.info(f"Connecting to SHTTP endpoint: {command_or_url}...")
            async with streamablehttp_client(command_or_url) as streams:
                await run_streamablehttp_session(*streams, tool_to_call=tool_name, tool_args=tool_args)
    else:
        # Use stdio client for commands
        server_parameters = StdioServerParameters(command=command_or_url, args=args, env=env_dict)
        async with stdio_client(server_parameters) as streams:
            await run_session(*streams, tool_to_call=tool_name, tool_args=tool_args)


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("command_or_url", help="Command or URL to connect to")
    parser.add_argument("args", nargs="*", help="Additional arguments")
    parser.add_argument(
        "-e",
        "--env",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        help="Environment variables to set. Can be used multiple times.",
        default=[],
    )
    parser.add_argument(
        "--tool",
        help="Name of the tool to call directly",
    )
    parser.add_argument(
        "--arg",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        help="Tool argument (key-value pair). Can be used multiple times.",
        default=[],
    )

    args = parser.parse_args()
    
    # If a specific tool is requested
    if args.tool:
        tool_args = {k: v for k, v in args.arg}
        anyio.run(partial(main, args.command_or_url, args.args, args.env, args.tool, tool_args), backend="trio")
    else:
        anyio.run(partial(main, args.command_or_url, args.args, args.env), backend="trio")


if __name__ == "__main__":
    cli()
