from typing import Dict, Tuple

from tilecloud import TileLayout


class WMTSTileLayout(TileLayout):
    def __init__(
        self,
        url: str = "",
        layer: str = None,
        style: str = None,
        format: str = None,
        tile_matrix_set: str = None,
        tile_matrix: type = str,
        dimensions_name: Tuple[str] = (),
        request_encoding: str = "KVP",
    ) -> None:
        self.url = url
        self.layer = layer
        self.style = style
        self.format = format
        self.tile_matrix_set = tile_matrix_set
        self.tile_matrix = tile_matrix
        self.dimensions_name = dimensions_name
        self.request_encoding = request_encoding

        if self.request_encoding == "KVP":
            if not self.url or self.url[-1] != "?":
                self.url += "?"
        elif self.url and self.url[-1] != "/":
            self.url += "/"

    def filename(self, tilecoord: TileCoord, metadata: Dict[str, str] = None) -> str:
        metadata = {} if metadata is None else metadata
        # Careful the order is important for the REST request encoding
        query = []
        if self.request_encoding == "KVP":
            query.extend([("Service", "WMTS"), ("Request", "GetTile"), ("Format", self.format)])

        query.extend([("Version", "1.0.0"), ("Layer", self.layer), ("Style", self.style)])

        for name in self.dimensions_name:
            query.append((name, metadata["dimension_" + name]))

        query.extend(
            [
                ("TileMatrixSet", self.tile_matrix_set),
                ("TileMatrix", str(self.tile_matrix(tilecoord.z))),
                ("TileRow", str(tilecoord.y)),
                ("TileCol", str(tilecoord.x)),
            ]
        )
        if self.request_encoding == "KVP":
            return self.url + "&".join("=".join(p) for p in query)
        else:
            return self.url + "/".join(p[1] for p in query) + self.format
