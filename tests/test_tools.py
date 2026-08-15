from agent.tools.filesystem import build_filesystem_tools
from agent.tools.memory import build_memory_tools
from agent.tools.todo import build_todo_tools


def test_write_read_edit_roundtrip(tmp_path):
    tools = {t.name: t for t in build_filesystem_tools(str(tmp_path))}

    write_result = tools["write_file"].run(path="a.txt", content="hello\nworld\n")
    assert write_result.ok

    read_result = tools["read_file"].run(path="a.txt")
    assert "1: hello" in read_result.output
    assert "2: world" in read_result.output

    edit_result = tools["edit_file"].run(path="a.txt", old_text="world", new_text="there")
    assert edit_result.ok

    read_again = tools["read_file"].run(path="a.txt")
    assert "there" in read_again.output


def test_workspace_guard_blocks_path_escape(tmp_path):
    tools = {t.name: t for t in build_filesystem_tools(str(tmp_path))}
    result = tools["read_file"].run(path="../../etc/passwd")
    assert not result.ok


def test_search_files(tmp_path):
    tools = {t.name: t for t in build_filesystem_tools(str(tmp_path))}
    tools["write_file"].run(path="x.py", content="def foo():\n    return 42\n")
    result = tools["search_files"].run(query="foo")
    assert "x.py" in result.output


def test_memory_tools_persist(tmp_path):
    mem_path = tmp_path / "mem.json"
    tools = {t.name: t for t in build_memory_tools(str(mem_path))}
    tools["memory_set"].run(key="favorite_color", value="blue")
    result = tools["memory_get"].run(key="favorite_color")
    assert result.output == "blue"
    assert mem_path.exists()


def test_todo_tools():
    tools = {t.name: t for t in build_todo_tools()}
    add_result = tools["todo_add"].run(text="write tests")
    assert "Added todo #1" in add_result.output
    complete_result = tools["todo_complete"].run(id=1)
    assert complete_result.ok
    listing = tools["todo_list"].run()
    assert "[x] #1" in listing.output
