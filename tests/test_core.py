import io, json, os, sys, tempfile, types, unittest, zipfile
from pathlib import Path

HOME = tempfile.mkdtemp(prefix="nl_home_")
os.environ["HOME"] = HOME
os.environ["USERPROFILE"] = HOME

# ---- finti minecraft_launcher_lib e requests -------------------------------------------------
CALLS = []
mll = types.ModuleType("minecraft_launcher_lib")
mll.install = types.SimpleNamespace(install_minecraft_version=lambda v, d, callback=None: CALLS.append(("vanilla", v)))
class FakeLoader:
    def __init__(self, i): self.i = i
    def get_name(self): return self.i.title()
    def is_minecraft_version_supported(self, v): return v != "0.0"
    def install(self, mc, d, loader_version=None, callback=None, java=None):
        CALLS.append(("loader", self.i, mc, loader_version)); return f"{self.i}-{mc}-{loader_version or 'latest'}"
mll.mod_loader = types.SimpleNamespace(get_mod_loader=lambda i: FakeLoader(i))
def fake_install_mrpack(path, d, modpack_directory=None, callback=None):
    CALLS.append(("mrpack", path)); Path(modpack_directory, "mods").mkdir(parents=True, exist_ok=True)
mll.mrpack = types.SimpleNamespace(install_mrpack=fake_install_mrpack, get_mrpack_launch_version=lambda p: "fabric-loader-0.15.7-1.20.1", get_mrpack_information=lambda p: {})
sys.modules["minecraft_launcher_lib"] = mll

class Resp:
    def __init__(self, url, body=b"JAR", status=200, headers=None):
        self.url, self.body, self.status_code, self.headers = url, body, status, headers or {}
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(f"HTTP {self.status_code}")
    def iter_content(self, n): yield self.body
    def json(self): return {}
    def __enter__(self): return self
    def __exit__(self, *a): return False
def fake_get(url, **kw):
    CALLS.append(("get", url))
    if "/files/222/" in url: return Resp(url, status=403)
    if "/files/111/" in url: return Resp("https://edge.forgecdn.net/files/1/111/CoolMod-1.0.jar")
    if "/files/333/" in url: return Resp("https://edge.forgecdn.net/files/1/333/Pretty%20Pack.zip")
    return Resp(url, headers={"content-disposition": 'attachment; filename="pack.zip"'})
req = types.ModuleType("requests"); req.get = fake_get
sys.modules["requests"] = req

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nolimits.core import importer, runtime, modpacks
from nolimits.core.instances import InstanceStore

def make_zip(path, files):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items(): z.writestr(name, data)
    return path

TMP = Path(tempfile.mkdtemp(prefix="nl_zips_"))

class Core(unittest.TestCase):
    def setUp(self):
        CALLS.clear()
        for f in (runtime.ROOT / "instances.json",): f.unlink(missing_ok=True)

    def test_loader_keys(self):
        self.assertEqual(runtime.loader_from_dependencies({"minecraft": "1.20.1", "fabric-loader": "0.15.7"}), ("fabric", "0.15.7"))
        self.assertEqual(runtime.loader_from_dependencies({"quilt-loader": "0.2"}), ("quilt", "0.2"))
        self.assertEqual(runtime.loader_from_dependencies({"neoforge": "21.1.1"}), ("neoforge", "21.1.1"))
        self.assertEqual(runtime.loader_from_dependencies({"forge": "47.2.0"}), ("forge", "47.2.0"))
        self.assertEqual(runtime.loader_from_dependencies({"minecraft": "1.20.1"}), ("vanilla", ""))

    def test_parse_loader_id(self):
        self.assertEqual(runtime.parse_loader_id("forge-47.2.0"), ("forge", "47.2.0"))
        self.assertEqual(runtime.parse_loader_id("neoforge-21.1.1"), ("neoforge", "21.1.1"))
        self.assertEqual(runtime.parse_loader_id("boh-1"), ("vanilla", ""))

    def test_detect_formats(self):
        mr = make_zip(TMP / "a.mrpack", {"modrinth.index.json": json.dumps({"dependencies": {"minecraft": "1.20.1"}})})
        cf = make_zip(TMP / "b.zip", {"manifest.json": json.dumps({"minecraft": {"version": "1.20.1"}, "files": []})})
        pr = make_zip(TMP / "c.zip", {"Inst/instance.cfg": "name=X", "Inst/mmc-pack.json": "{}"})
        bad = make_zip(TMP / "d.zip", {"readme.txt": "x"})
        self.assertEqual(importer.detect_format(mr), "modrinth")
        self.assertEqual(importer.detect_format(cf), "curseforge")
        self.assertEqual(importer.detect_format(pr), "prism")
        with self.assertRaises(ValueError): importer.detect_format(bad)
        notzip = TMP / "e.zip"; notzip.write_text("no")
        with self.assertRaises(ValueError): importer.detect_format(notzip)

    def test_import_mrpack(self):
        idx = {"name": "Super Pack", "summary": "bello", "dependencies": {"minecraft": "1.20.1", "fabric-loader": "0.15.7"}}
        item = importer.import_modpack(make_zip(TMP / "s.mrpack", {"modrinth.index.json": json.dumps(idx)}))
        self.assertEqual((item["name"], item["minecraft_version"], item["loader"], item["loader_version"]), ("Super Pack", "1.20.1", "fabric", "0.15.7"))
        self.assertEqual(item["status"], "installed"); self.assertTrue(Path(item["directory"]).is_dir())
        self.assertEqual(item["launch_version"], "fabric-loader-0.15.7-1.20.1")
        # secondo import dello stesso pack: nome e cartella devono essere unici
        again = importer.import_modpack(TMP / "s.mrpack")
        self.assertEqual(again["name"], "Super Pack (2)"); self.assertNotEqual(item["directory"], again["directory"])
        self.assertEqual(len(InstanceStore().list_instances()), 2)

    def test_import_curseforge(self):
        manifest = {"name": "CF Pack", "author": "io", "minecraft": {"version": "1.20.1", "modLoaders": [{"id": "forge-47.2.0", "primary": True}]},
                    "overrides": "overrides", "files": [{"projectID": 1, "fileID": 111, "required": True}, {"projectID": 2, "fileID": 222, "required": True}, {"projectID": 3, "fileID": 333}]}
        z = make_zip(TMP / "cf.zip", {"manifest.json": json.dumps(manifest), "overrides/config/a.toml": "x=1", "overrides/../../evil.txt": "pwn"})
        steps = []
        item = importer.import_modpack(z, progress=lambda v, m: steps.append(v))
        d = Path(item["directory"])
        self.assertEqual((item["loader"], item["loader_version"], item["launch_version"]), ("forge", "47.2.0", "forge-1.20.1-47.2.0"))
        self.assertTrue((d / "config" / "a.toml").is_file())
        self.assertTrue((d / "mods" / "CoolMod-1.0.jar").is_file())
        self.assertTrue((d / "resourcepacks" / "Pretty Pack.zip").is_file())          # .zip -> resourcepacks
        self.assertEqual(len(item["import_warnings"]), 1); self.assertIn("222", item["import_warnings"][0])
        self.assertFalse((d.parent.parent / "evil.txt").exists() or (d.parent / "evil.txt").exists() or Path(HOME, "evil.txt").exists())
        self.assertEqual(steps[-1], 100); self.assertEqual(steps, sorted(steps))       # progresso mai all'indietro

    def test_import_prism(self):
        cfg = "[General]\nname=Il Mio Prism\nIntendedVersion=1.19.2\nOverrideMemory=true\nMinMemAlloc=1024\nMaxMemAlloc=6144\nOverrideJavaArgs=true\nJvmArgs=-XX:+UseG1GC\nnotes=ciao\n"
        pack = {"components": [{"uid": "net.minecraft", "version": "1.20.1"}, {"uid": "net.fabricmc.fabric-loader", "version": "0.15.7"}]}
        z = make_zip(TMP / "pr.zip", {"MyInst/instance.cfg": cfg, "MyInst/mmc-pack.json": json.dumps(pack),
                                      "MyInst/.minecraft/mods/m.jar": "J", "MyInst/.minecraft/options.txt": "o", "MyInst/.minecraft/../../../evil2.txt": "pwn", "MyInst/other.txt": "no"})
        item = importer.import_modpack(z, name="Custom")
        d = Path(item["directory"])
        self.assertEqual((item["name"], item["minecraft_version"], item["loader"], item["loader_version"]), ("Custom", "1.20.1", "fabric", "0.15.7"))
        self.assertEqual((item["memory_min"], item["memory_max"], item["jvm_args"], item["notes"]), (1024, 6144, "-XX:+UseG1GC", "ciao"))
        self.assertTrue((d / "mods" / "m.jar").is_file()); self.assertTrue((d / "options.txt").is_file()); self.assertFalse((d / "other.txt").exists())
        self.assertIn(("loader", "fabric", "1.20.1", "0.15.7"), CALLS)

    def test_failed_import_cleans_up(self):
        z = make_zip(TMP / "bad.zip", {"manifest.json": json.dumps({"minecraft": {"version": "0.0", "modLoaders": [{"id": "forge-1", "primary": True}]}, "files": []})})
        before = set(p.name for p in runtime.INSTANCES_DIR.glob("*")) if runtime.INSTANCES_DIR.exists() else set()
        with self.assertRaises(RuntimeError): importer.import_modpack(z)           # 0.0 non supportato dal finto forge
        after = set(p.name for p in runtime.INSTANCES_DIR.glob("*")) if runtime.INSTANCES_DIR.exists() else set()
        self.assertEqual(before, after); self.assertEqual(InstanceStore().list_instances(), [])

    def test_url_direct_download_and_errors(self):
        idx = {"dependencies": {"minecraft": "1.20.1"}}
        orig = req.get
        def get(url, **kw):
            if url.endswith("/p.mrpack"):
                buf = io.BytesIO(); zipfile.ZipFile(buf, "w").writestr("modrinth.index.json", json.dumps(idx))
                return Resp(url, body=buf.getvalue(), headers={"content-length": str(len(buf.getvalue()))})
            return orig(url, **kw)
        req.get = get
        try:
            item = importer.import_modpack("https://example.com/p.mrpack")
            self.assertEqual(item["minecraft_version"], "1.20.1")
        finally: req.get = orig
        with self.assertRaises(RuntimeError): importer.import_modpack("https://www.curseforge.com/minecraft/modpacks/x")
        with self.assertRaises(FileNotFoundError): importer.import_modpack("/non/esiste.zip")
        with self.assertRaises(ValueError): importer.import_modpack("   ")

    def test_runtime_and_instance_install(self):
        self.assertEqual(runtime.install_runtime("1.20.1", "vanilla"), "1.20.1")
        self.assertEqual(runtime.install_runtime("1.20.1", "fabric", "0.15.7"), "fabric-1.20.1-0.15.7")
        with self.assertRaises(RuntimeError): runtime.install_runtime("0.0", "fabric")
        with self.assertRaises(ValueError): runtime.install_runtime("1.20.1", "liteloader")
        store = InstanceStore(); item = store.add_instance("Nuova", "1.20.1", "forge")
        done = runtime.install_instance(item)
        self.assertEqual((done["status"], done["launch_version"]), ("installed", "forge-1.20.1-latest")); self.assertTrue(Path(done["directory"]).is_dir())

    def test_duplicate(self):
        idx = {"dependencies": {"minecraft": "1.20.1"}}
        item = importer.import_modpack(make_zip(TMP / "dup.mrpack", {"modrinth.index.json": json.dumps(idx)}), name="Orig")
        (Path(item["directory"]) / "mods" / "x.jar").write_text("J")
        store = InstanceStore(); copy = store.duplicate_instance(item["id"], "Orig copia")
        self.assertNotEqual(copy["id"], item["id"]); self.assertNotEqual(copy["directory"], item["directory"])
        self.assertTrue((Path(copy["directory"]) / "mods" / "x.jar").is_file())
        with self.assertRaises(ValueError): store.duplicate_instance(item["id"], "orig COPIA")
        self.assertTrue(store.name_taken("ORIG")); self.assertFalse(store.name_taken("ORIG", ignore_id=item["id"]))

    def test_launch_options(self):
        o = modpacks.instance_launch_options({"memory_min": 1024, "memory_max": 4096, "jvm_args": "-XX:+UseG1GC -Dfoo=bar", "java_path": " /usr/bin/java ", "resolution_width": 1280, "resolution_height": 720})
        self.assertEqual(o["jvmArguments"], ["-Xms1024M", "-Xmx4096M", "-XX:+UseG1GC", "-Dfoo=bar"])
        self.assertEqual((o["executablePath"], o["customResolution"], o["resolutionWidth"], o["resolutionHeight"]), ("/usr/bin/java", True, "1280", "720"))
        self.assertEqual(modpacks.instance_launch_options({}), {})
        self.assertEqual(modpacks.instance_launch_options({"memory_min": 0, "memory_max": "", "resolution_width": 800}), {})

if __name__ == "__main__":
    unittest.main(verbosity=2)
