"""Tests for CLI module."""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from chronicle import cli
from tests.helpers import create_temp_repo


class TestCLIBuildParser(unittest.TestCase):
    def test_parser_creation(self):
        parser = cli.build_parser()
        self.assertIsNotNone(parser)

    def test_version(self):
        parser = cli.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["--version"])

    def test_no_command(self):
        parser = cli.build_parser()
        args = parser.parse_args([])
        self.assertIsNone(args.command)


class TestCLIAnalyze(unittest.TestCase):
    def setUp(self):
        self.repo = create_temp_repo()
        self.old_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_analyze_output(self):
        args = type("Args", (), {
            "repo": self.repo, "max": None, "since": None,
            "until": None, "json": False, "output": None, "no_network": False,
        })()
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = cli.cmd_analyze(args)
        output = buf.getvalue()
        self.assertIn("Commits", output)
        self.assertIn("Authors", output)

    def test_analyze_json(self):
        args = type("Args", (), {
            "repo": self.repo, "max": None, "since": None,
            "until": None, "json": True, "output": None, "no_network": False,
        })()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.cmd_analyze(args)
        output = buf.getvalue()
        data = json.loads(output)
        self.assertIn("repo", data)
        self.assertIn("summary", data)

    def test_analyze_export(self):
        outfile = os.path.join(tempfile.mkdtemp(), "out.json")
        args = type("Args", (), {
            "repo": self.repo, "max": None, "since": None,
            "until": None, "json": False, "output": outfile, "no_network": False,
        })()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.cmd_analyze(args)
        self.assertTrue(os.path.exists(outfile))

    def test_analyze_invalid_repo(self):
        args = type("Args", (), {
            "repo": "/nonexistent/path", "max": None, "since": None,
            "until": None, "json": False, "output": None, "no_network": False,
        })()
        with self.assertRaises(SystemExit):
            cli.cmd_analyze(args)


class TestCLIAuthors(unittest.TestCase):
    def setUp(self):
        self.repo = create_temp_repo()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_authors_output(self):
        args = type("Args", (), {
            "repo": self.repo, "max": None, "sort_by": "commits",
            "limit": 20, "json": False,
        })()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.cmd_authors(args)
        output = buf.getvalue()
        self.assertIn("Alice", output)
        self.assertIn("Bob", output)


class TestCLIFiles(unittest.TestCase):
    def setUp(self):
        self.repo = create_temp_repo()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_files_output(self):
        args = type("Args", (), {
            "repo": self.repo, "max": None, "sort_by": "commits", "limit": 30,
        })()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.cmd_files(args)
        output = buf.getvalue()
        self.assertIn("main.py", output)


class TestCLITimeline(unittest.TestCase):
    def setUp(self):
        self.repo = create_temp_repo()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_timeline_output(self):
        args = type("Args", (), {
            "repo": self.repo, "max": None, "granularity": "monthly", "limit": 30,
        })()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.cmd_timeline(args)
        output = buf.getvalue()
        self.assertIn("2024-01", output)


class TestCLINetwork(unittest.TestCase):
    def setUp(self):
        self.repo = create_temp_repo()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_network_output(self):
        args = type("Args", (), {
            "repo": self.repo, "max": None, "limit": 20,
        })()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.cmd_network(args)
        output = buf.getvalue()
        self.assertIn("Network", output)


class TestCLITrend(unittest.TestCase):
    def setUp(self):
        self.repo = create_temp_repo()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_trend_output(self):
        args = type("Args", (), {
            "repo": self.repo, "max": None, "limit": 30,
        })()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.cmd_trend(args)
        output = buf.getvalue()
        self.assertIn("Est. LOC", output)


class TestCLIMilestones(unittest.TestCase):
    def setUp(self):
        self.repo = create_temp_repo()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_milestones_output(self):
        args = type("Args", (), {
            "repo": self.repo, "max": None, "limit": 20,
        })()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.cmd_milestones(args)
        output = buf.getvalue()
        self.assertIn("Date", output)


class TestCLIExport(unittest.TestCase):
    def setUp(self):
        self.repo = create_temp_repo()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_export_json(self):
        outfile = os.path.join(tempfile.mkdtemp(), "report.json")
        args = type("Args", (), {
            "repo": self.repo, "max": None, "format": "json", "output": outfile,
        })()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.cmd_export(args)
        self.assertTrue(os.path.exists(outfile))

    def test_export_markdown(self):
        outfile = os.path.join(tempfile.mkdtemp(), "report.md")
        args = type("Args", (), {
            "repo": self.repo, "max": None, "format": "markdown", "output": outfile,
        })()
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.cmd_export(args)
        self.assertTrue(os.path.exists(outfile))
        with open(outfile, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("# Chronicle Report", content)


class TestCLIMain(unittest.TestCase):
    def test_main_no_args(self):
        old_argv = sys.argv
        sys.argv = ["chronicle"]
        with self.assertRaises(SystemExit) as cm:
            cli.main()
        self.assertEqual(cm.exception.code, 0)
        sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
