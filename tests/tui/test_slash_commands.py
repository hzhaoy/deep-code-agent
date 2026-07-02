"""Tests for slash command filtering."""


def test_slash_commands_show_all_for_empty_slash_query():
    from deep_code_agent.tui.commands import filter_slash_commands

    names = [command.name for command in filter_slash_commands("/")]

    assert names[:3] == ["/help", "/clear", "/skills"]
    assert "/exit" in names


def test_slash_commands_prioritize_prefix_matches():
    from deep_code_agent.tui.commands import filter_slash_commands

    names = [command.name for command in filter_slash_commands("/cl")]

    assert names[0] == "/clear"


def test_slash_commands_match_substrings():
    from deep_code_agent.tui.commands import filter_slash_commands

    names = [command.name for command in filter_slash_commands("/odel")]

    assert names == ["/model"]


def test_slash_commands_ignore_non_command_text():
    from deep_code_agent.tui.commands import filter_slash_commands

    assert filter_slash_commands("please /clear") == []
    assert filter_slash_commands("/clear now") == []
