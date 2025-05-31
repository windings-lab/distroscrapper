from __future__ import annotations

import os.path
import sys
from concurrent.futures import ThreadPoolExecutor

import httpx
from bs4 import BeautifulSoup
from graphviz import Digraph

from util import dump_json, read_json, read_html

headers = httpx.Headers({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0'})
limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
client = httpx.Client(limits=limits, headers=headers)
base_url = "https://distrowatch.com/"

def get_html(url: str, cache_name: str):
    cache_file = "cache/" + cache_name + ".html"
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    if os.path.isfile(cache_file) and os.path.getsize(cache_file) > 0:
        print(f"Using cached html <{cache_name}>")
        html = read_html(cache_file)
    else:
        print(f"Requesting <{cache_name}>")
        try:
            response = client.get(url=url)
        except Exception as e:
            print(e)
            sys.exit()

        html = response.text

        # Writing html to cache
        with open(cache_file, "wb") as f:
            f.write(response.content)

    return html


def create_distro_links():
    query_url = "https://distrowatch.com/search.php?ostype=All&category=All&origin=All&basedon=All&notbasedon=None&desktop=All&architecture=All&package=All&rolling=All&isosize=All&netinstall=All&language=All&defaultinit=All&status=All#advanced"
    query_html = get_html(query_url, "query")
    query_parser = BeautifulSoup(query_html, "lxml")

    distro_a_tags = query_parser.find_all("td", class_="NewsText")[1].find_all("a")[5:]
    distro_links = [
        (
            base_url + "table.php?distribution=" + a_tag["href"],
            a_tag["href"]
        )
        for a_tag in distro_a_tags
        if a_tag.parent.name == "b"
    ]

    return distro_links

class Distro:
    def __init__(
        self,
        name: str,
        url: str,
        based_on: Distro | None,
        is_parent: bool,
        image_file: str,
    ):
        self.name = name
        self.url = url
        self.based_on = based_on
        self.children = []
        self.is_parent = is_parent
        self.is_leaf = False
        self.image_file = image_file
        self.graph = None
        self.node = None

    def subgraph(self, global_graph: Digraph):
        if self.based_on is not None:
            self.based_on.graph.subgraph(self.graph)
            self.based_on.subgraph(global_graph)
        else:
            global_graph.subgraph(self.graph)

    @property
    def leaf_level(self):
        index = 0

        based_on = self.based_on
        while based_on is not None:
            index += 1
            based_on = based_on.based_on

        return index

    def __str__(self):
        return self.name

class DistroBuilder:
    def __init__(self, name, url, html):
        self.name = name
        self.url = url
        self.html = html
        self.parser = None
        self.is_parent = None
        self.based_on = None
        self.image_file = None

    def to_dict(self):
        return {
            "name": self.name,
            "url": self.url,
            "is_parent": self.is_parent,
            "based_on": self.based_on,
            "image_file": self.image_file,
        }

    def set_parser(self, parser: BeautifulSoup):
        self.parser = parser

    def set_is_parent(self, is_parent):
        self.is_parent = is_parent

    def set_based_on(self, based_on):
        self.based_on = based_on

    def set_image_file(self, image_file):
        self.image_file = image_file

    def build(self) -> Distro:
        distro = Distro(
            name=self.name.capitalize(),
            url=self.url,
            image_file=self.image_file,
            based_on=self.based_on,
            is_parent=self.is_parent,
        )

        return distro

    def __str__(self):
        if not self.based_on:
            return self.name
        else:
            based_on_name = self.based_on if isinstance(self.based_on, str) else self.based_on.name

        return f"{self.name} -> {based_on_name}"


def create_distro_parser(builder: DistroBuilder):
    print(f"Creating distro parser <{builder.name}>")
    parser = BeautifulSoup(builder.html, "lxml")

    builder.set_parser(parser)

    return builder


def parse_distros(distro_builders: list[DistroBuilder], json_file: str):
    for distro_builder in distro_builders:
        def parse_based_on_and_is_parent():
            table = distro_builder.parser.find("td", class_="TablesTitle")
            _based_on = table.find("ul").find_all("li")[1].find_all("a")

            if not _based_on:
                _is_parent = True
            else:
                _is_parent = False
                _based_on = _based_on[-1].text.lower()

            return _based_on, _is_parent
        def parse_and_get_image():
            image_file = "cache/distros/" + distro_builder.name + ".png"
            if os.path.isfile(image_file):
                print(f"Using cached image <{image_file}>")
                return image_file

            print(f"Parsing image for distro <{distro_builder.name}>")
            table_title = distro_builder.parser.find("td", class_="TablesTitle")
            image_tag = table_title.find("img")
            image_src = image_tag.get("src")
            image_url = base_url + image_src
            print(f"Requesting image for distro <{distro_builder.name}>")
            try:
                response = client.get(url=image_url)
            except Exception as e:
                print(e)
                sys.exit()

            with open(image_file, "wb") as f:
                f.write(response.content)

            return image_file

        print(f"Parsing <{distro_builder.name}>")

        based_on, is_parent = parse_based_on_and_is_parent()
        image_file = parse_and_get_image()

        distro_builder.set_is_parent(is_parent)
        if not is_parent:
            distro_builder.set_based_on(based_on)
        distro_builder.set_image_file(image_file)

    dump_json(json_file, distro_builders)


mapping = {
    "ubuntu (lts)": "ubuntu",
    "ubuntu lts": "ubuntu",
    "debian (testing)": "debian",
    "debian (unstable)": "debian",
    "debian (stable)": "debian",
    "debian (lts)": "debian",
    "red hat": "redhat",
    "lfs (formerly based on puppy)": "puppy",
    "damn small": "damnsmall",
    "lubuntu (lts)": "lubuntu",
    "mx linux": "mx",
    "raspbian": "raspios",
    "arch linux": "arch",
    "android": "androidx86",
    "mandrake": "mandriva",
    "lineageos": "androidx86",
    "red hat enterprise linux": "redhat",
    "m0n0wall": "freebsd",
    "peanut": "alinux",
    "caldera": "sco",
    "kde neon": "kdeneon",
    "sidux": "aptosid",
    "tiny core": "tinycore",
    "indpenendent": None
}
def fix_based_on(distros: list[Distro]):
    distro_to_fix = []
    for distro in distros:
        if distro.is_parent:
            continue

        # In parse_distro based_on is str
        # Here I am converting it to actual distro
        based_on = distro.based_on
        based_on = mapping.get(based_on, based_on)
        based_on = based_on.capitalize() if based_on else None
        it_was_set = False

        if based_on == distro.name or based_on == "" or based_on is None:
            it_was_set = True
            distro.is_parent = True
            distro.based_on = None

        for other_distro in distros:
            if distro is other_distro:
                continue

            if based_on == other_distro.name:
                distro.based_on = other_distro
                it_was_set = True

            if it_was_set:
                break

        # If there are any updates to distrowatch
        # Check distro_to_fix array
        # And add string mapping items
        # Example:
        # LUbuntu distro has on its website Based on:
        # with "ubuntu (lts)". But Ubuntu website has only "ubuntu" keyword. SO
        # Add mapping "ubuntu (lts)" -> "ubuntu" in mapping variable
        # Check by yourself by removing some entry from mapping
        if not it_was_set:
            distro_to_fix.append(distro)


def add_children(distros: list[Distro]):
    for distro in distros:
        for other_distro in distros:
            if distro is other_distro:
                continue

            if other_distro.based_on is distro:
                distro.children.append(other_distro)
        if len(distro.children) == 0:
            distro.is_leaf = True


def create_graph(distros):
    dot = Digraph(name='Linux Distros')
    dot.attr(splines="ortho", packmode="graph", rankdir="LR", bgcolor="#9E7741")

    def font_size(connections: int):
        return str(10 + connections * 2)

    def width(connections: int):
        return str(0.75 + 0.05 * connections)

    def create_node_custom_size(graph, distro):
        connections = len(distro.children)

        return graph.node(
            distro.name,
            fontsize=font_size(connections),
            width=width(connections),
            height="0.5",
            fixedsize="false",
            shape="box",
            URL=distro.url,
            image=distro.image_file,
        )

    def create_node_fixed_size(graph, distro):
        return graph.node(
            distro.name,
            shape="box",
            URL=distro.url,
            image=distro.image_file,
        )

    for distro in distros:
        if distro.is_leaf:
            continue

        print(f"Create cluster graph for non-leaf distro {distro.name}")
        distro.graph = Digraph(name=f"cluster_{distro.name}")
        distro.graph.attr(style='rounded', color='red', penwidth='3', label=distro.name)


    for distro in distros:
        if distro.is_leaf:
            continue

        print(f"Add node and edge for non-leaf distro {distro.name}")
        distro.node = create_node_custom_size(distro.graph, distro)

        if distro.based_on:
            distro.based_on.graph.edge(distro.name, distro.based_on.name, color='green', penwidth='2')

    distros_with_no_dependencies = Digraph(name="cluster_DistrosWithNoDependencies")
    distros_with_no_dependencies.attr(penwidth='3', label="Distros with no dependencies")
    for distro in distros:
        if not distro.is_leaf:
            continue

        print(f"Add node and edge for leaf distro {distro.name}")
        if distro.based_on is not None:
            distro.node = create_node_fixed_size(distro.based_on.graph, distro)
            distro.based_on.graph.edge(distro.name, distro.based_on.name)
        else:
            distro.node = create_node_fixed_size(distros_with_no_dependencies, distro)

    dot.subgraph(distros_with_no_dependencies)

    graphs_by_level = {}
    for distro in distros:
        if distro.is_leaf:
            continue
        key = distro.leaf_level
        graphs_by_level.setdefault(key, []).append((distro.graph, distro.based_on))

    for leaf_level in sorted(graphs_by_level, reverse=True):
        for graph, distro_based in graphs_by_level[leaf_level]:
            if distro_based:
                distro_based.graph.subgraph(graph)
            else:
                dot.subgraph(graph)


    dot.render('distros_graph', format='pdf', view=True)


def main():
    parser_cache_file = "cache/parser_cache.json"
    if not os.path.isfile(parser_cache_file):
        print("Creating new parser")
        distro_links = create_distro_links()

        distro_builders: list[DistroBuilder] = []
        for distro_link, distro_name in distro_links:
            distro_html = get_html(distro_link, "distros/" + distro_name)
            distro_builders.append(DistroBuilder(distro_name, distro_link, distro_html))

        with ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
            distro_builders = list(executor.map(create_distro_parser, distro_builders))

        parse_distros(distro_builders, parser_cache_file)
    else:
        print("Using parser cache")

        parser_cache_data = read_json(parser_cache_file)
        distro_builders: list[DistroBuilder] = []
        for item in parser_cache_data:
            name = item["name"]
            print(f"Using parser cache <{name}>")
            url = item["url"]
            html = None
            distro_builder = DistroBuilder(name, url, html)

            is_parent = item["is_parent"]
            based_on = item["based_on"]
            image_file = item["image_file"]

            distro_builder.set_is_parent(is_parent)
            distro_builder.set_based_on(based_on)
            distro_builder.set_image_file(image_file)

            distro_builders.append(distro_builder)

    distros = [distro_builder.build() for distro_builder in distro_builders]
    fix_based_on(distros)
    add_children(distros)

    create_graph(distros)

    client.close()


if __name__ == "__main__":
    main()