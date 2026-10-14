# Maintainer: automateyournetwork
pkgname=netclaw
pkgver=1.10.0
pkgrel=1
pkgdesc='Network engineering agent with optional, user-selected runtime and integrations'
arch=('any')
url='https://github.com/automateyournetwork/netclaw'
license=('Apache-2.0' '0BSD')
depends=('bash' 'python>=3.11' 'git' 'curl' 'coreutils' 'nodejs>=22' 'npm' 'uv')
checkdepends=('desktop-file-utils')
options=('!strip' '!debug' '!purge' 'libtool' 'staticlibs')
_commit=eb5475e46c7339bb289228d2017b3c20be209fe3
source=("$pkgname-$pkgver.tar.gz::$url/archive/$_commit.tar.gz"
        'netclaw' 'netclaw.desktop' 'launcher.py' 'test_launcher.py' 'LICENSE')
sha256sums=('708dd2d113cd077e6d67c1954f1401efdf11be20221c1cb600fa520cafb64528'
            'c45225a6c1e9faf64761389b3e2405c5b747a932145d2a0ad8b338f67fd397f0'
            '17786f8ccb26c4ccf5ffbf8b923ec1137a3234fa1044edfbf2c54c475760f3be'
            '99dcefc0b8f8cc1c95060c2ed220c17ff8433a629fbea8e5df43611f78a2349e'
            'c8952acc2bb529f37837da93d609658de7c22e985ad82e2e3502bdbc4175fab8'
            '6097e39049c27d089a23606490d089aed57d14e3a9d6601504386fb34f2cb47f')

check() {
  python -m unittest -v test_launcher.py
  desktop-file-validate netclaw.desktop
  bash -n netclaw
}

package() {
  install -d "$pkgdir/usr/share/netclaw/source"
  cp -a "netclaw-$_commit/." "$pkgdir/usr/share/netclaw/source/"
  install -Dm755 netclaw "$pkgdir/usr/bin/netclaw"
  install -Dm644 launcher.py "$pkgdir/usr/lib/netclaw/launcher.py"
  install -Dm644 netclaw.desktop "$pkgdir/usr/share/applications/netclaw.desktop"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/packaging-LICENSE"
  install -Dm644 "netclaw-$_commit/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  python - "$pkgdir/usr/share/netclaw" "$_commit" <<'PY'
import json
from pathlib import Path
import sys
from launcher import manifest
package = Path(sys.argv[1])
(package / 'manifest.json').write_text(json.dumps(manifest(package / 'source', sys.argv[2]), sort_keys=True) + '\n')
PY
}
