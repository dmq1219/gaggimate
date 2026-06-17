# Flashing this firmware

**Languages:** [English](#english) · [Español](#español) · [Italiano](#italiano)

> ⚠️ This is an **unofficial, personal fork** of GaggiMate with **display-only** UI
> changes (mode selector, animated brew/steam/water buttons, auto-sleep, battery
> overlay). It does **not** modify the controller, boiler logic, bootloader,
> partitions, or eFuses. The official firmware can always be re-flashed to revert.

---

## English

### What you need

- A GaggiMate setup with a **LilyGo T-RGB display** (ESP32-S3, 16 MB flash, 8 MB PSRAM)
  and a **GaggiMate Controller** board.
- The controller must run firmware that speaks **`PROTOCOL_VERSION` 3**. If the display
  shows *"Version mismatch, update controller"*, build the controller from this same
  repo: `pio run -e controller -t upload`.
- A **USB-C** cable. For the browser method, a Chromium browser (Chrome / Edge / Arc).

> 🔌 **Two boards, both appear as a serial port.** The display and the controller both
> enumerate as a USB serial device. Always confirm you are flashing the **display**:
> it has **16 MB flash + 8 MB PSRAM**. Read the chip info first with
> `esptool.py --port <PORT> flash_id` — flashing controller firmware onto the display
> (or vice-versa) results in a black screen (recoverable by re-flashing the right build).

### Option A — Flash a pre-built binary from your browser (no toolchain)

Ask the fork author for the single file **`display-merged.bin`** (see *Producing the
shareable binary* below), then:

1. Open **<https://espressif.github.io/esptool-js/>** in Chrome/Edge.
2. Set *Baudrate* to `921600`, click **Connect**, and select the display's serial port.
3. Add file **`display-merged.bin`** and set *Flash Address* to **`0x0`**.
4. Click **Program** and wait until it reports the data hash verified, then unplug/replug.

If *Connect* fails or the chip is not in download mode: **hold the BOOT (IO0) button,
tap RESET, release BOOT**, then click *Connect* again.

### Option B — Build and flash from source (developers)

```bash
git clone https://github.com/dmq1219/gaggimate.git -b feature/display-ux-redesign
cd gaggimate
# Prerequisites: PlatformIO Core, Python 3.11+, Node 18+
./scripts/build_webui.sh            # build + embed the web UI into the firmware
pio run -e display -t upload        # build + flash the display over USB
```

If both boards are connected, pass the port explicitly and confirm it is the display:
`pio run -e display -t upload --upload-port <PORT>`.

### Producing the shareable binary (for the author)

```bash
pio run -e display                  # produces .pio/build/display/*.bin
esptool.py --chip esp32s3 merge_bin -o display-merged.bin \
  --flash_mode qio --flash_freq 80m --flash_size 16MB \
  0x0      .pio/build/display/bootloader.bin \
  0x8000   .pio/build/display/partitions.bin \
  0xe000   docs/boot_app0.bin \
  0x10000  .pio/build/display/firmware.bin
```

Command-line flashing of that file (alternative to the browser):

```bash
esptool.py --chip esp32s3 --port <PORT> --baud 921600 write_flash 0x0 display-merged.bin
```

> 📦 *Optional — ship the coffee profiles too:* run `pio run -e display -t buildfs`, then
> add `0xc90000 .pio/build/display/littlefs.bin` to the `merge_bin` command. This
> overwrites the recipient's stored profiles/settings, so omit it if they should keep
> their own.

### Reverting to the official firmware

Flash the official GaggiMate display firmware from **<https://gaggimate.eu/>** (their web
flasher). Because this fork only changes the display app — nothing in the bootloader,
partition table, or flash security — the official build fully restores the device.

---

## Español

### Qué necesitas

- Un equipo GaggiMate con una **pantalla LilyGo T-RGB** (ESP32-S3, 16 MB de flash, 8 MB
  de PSRAM) y una placa **Controladora GaggiMate**.
- La controladora debe ejecutar firmware compatible con **`PROTOCOL_VERSION` 3**. Si la
  pantalla muestra *"Version mismatch, update controller"*, compila la controladora desde
  este mismo repositorio: `pio run -e controller -t upload`.
- Un cable **USB-C**. Para el método por navegador, un navegador Chromium (Chrome / Edge / Arc).

> 🔌 **Dos placas, ambas aparecen como puerto serie.** La pantalla y la controladora se
> detectan como un dispositivo serie USB. Confirma siempre que estás flasheando la
> **pantalla**: tiene **16 MB de flash + 8 MB de PSRAM**. Lee primero la información del
> chip con `esptool.py --port <PUERTO> flash_id` — flashear el firmware de la controladora
> en la pantalla (o al revés) deja la pantalla en negro (recuperable volviendo a flashear
> el firmware correcto).

### Opción A — Flashear un binario precompilado desde el navegador (sin herramientas)

Pide al autor del fork el archivo único **`display-merged.bin`** (ver *Generar el binario
compartible* más abajo) y luego:

1. Abre **<https://espressif.github.io/esptool-js/>** en Chrome/Edge.
2. Pon *Baudrate* en `921600`, pulsa **Connect** y elige el puerto serie de la pantalla.
3. Añade el archivo **`display-merged.bin`** y pon *Flash Address* en **`0x0`**.
4. Pulsa **Program** y espera a que confirme el hash de los datos; luego desconecta y vuelve a conectar.

Si *Connect* falla o el chip no está en modo de descarga: **mantén pulsado el botón BOOT
(IO0), pulsa RESET, suelta BOOT** y vuelve a pulsar *Connect*.

### Opción B — Compilar y flashear desde el código fuente (desarrolladores)

```bash
git clone https://github.com/dmq1219/gaggimate.git -b feature/display-ux-redesign
cd gaggimate
# Requisitos: PlatformIO Core, Python 3.11+, Node 18+
./scripts/build_webui.sh            # compila e incrusta la interfaz web en el firmware
pio run -e display -t upload        # compila y flashea la pantalla por USB
```

Si ambas placas están conectadas, indica el puerto explícitamente y confirma que es la
pantalla: `pio run -e display -t upload --upload-port <PUERTO>`.

### Generar el binario compartible (para el autor)

```bash
pio run -e display                  # genera .pio/build/display/*.bin
esptool.py --chip esp32s3 merge_bin -o display-merged.bin \
  --flash_mode qio --flash_freq 80m --flash_size 16MB \
  0x0      .pio/build/display/bootloader.bin \
  0x8000   .pio/build/display/partitions.bin \
  0xe000   docs/boot_app0.bin \
  0x10000  .pio/build/display/firmware.bin
```

Flasheo de ese archivo por línea de comandos (alternativa al navegador):

```bash
esptool.py --chip esp32s3 --port <PUERTO> --baud 921600 write_flash 0x0 display-merged.bin
```

> 📦 *Opcional — incluir también los perfiles de café:* ejecuta `pio run -e display -t buildfs`
> y añade `0xc90000 .pio/build/display/littlefs.bin` al comando `merge_bin`. Esto
> sobrescribe los perfiles/ajustes guardados del receptor, así que omítelo si quiere
> conservar los suyos.

### Volver al firmware oficial

Flashea el firmware oficial de la pantalla GaggiMate desde **<https://gaggimate.eu/>** (su
flasher web). Como este fork solo cambia la aplicación de la pantalla —nada del gestor de
arranque, la tabla de particiones ni la seguridad de la flash— la compilación oficial
restaura el dispositivo por completo.

---

## Italiano

### Cosa ti serve

- Un impianto GaggiMate con un **display LilyGo T-RGB** (ESP32-S3, 16 MB di flash, 8 MB di
  PSRAM) e una scheda **Controller GaggiMate**.
- Il controller deve eseguire un firmware che parli **`PROTOCOL_VERSION` 3**. Se il display
  mostra *"Version mismatch, update controller"*, compila il controller da questo stesso
  repository: `pio run -e controller -t upload`.
- Un cavo **USB-C**. Per il metodo via browser, un browser Chromium (Chrome / Edge / Arc).

> 🔌 **Due schede, entrambe compaiono come porta seriale.** Il display e il controller
> vengono rilevati come dispositivo seriale USB. Verifica sempre di flashare il **display**:
> ha **16 MB di flash + 8 MB di PSRAM**. Leggi prima le informazioni del chip con
> `esptool.py --port <PORTA> flash_id` — flashare il firmware del controller sul display
> (o viceversa) lascia lo schermo nero (recuperabile riflashando il firmware corretto).

### Opzione A — Flashare un binario precompilato dal browser (senza toolchain)

Chiedi all'autore del fork il file singolo **`display-merged.bin`** (vedi *Generare il
binario condivisibile* qui sotto), poi:

1. Apri **<https://espressif.github.io/esptool-js/>** in Chrome/Edge.
2. Imposta *Baudrate* su `921600`, premi **Connect** e seleziona la porta seriale del display.
3. Aggiungi il file **`display-merged.bin`** e imposta *Flash Address* su **`0x0`**.
4. Premi **Program** e attendi la conferma dell'hash dei dati; poi scollega e ricollega.

Se *Connect* fallisce o il chip non è in modalità download: **tieni premuto il pulsante BOOT
(IO0), premi RESET, rilascia BOOT** e premi di nuovo *Connect*.

### Opzione B — Compilare e flashare dai sorgenti (sviluppatori)

```bash
git clone https://github.com/dmq1219/gaggimate.git -b feature/display-ux-redesign
cd gaggimate
# Prerequisiti: PlatformIO Core, Python 3.11+, Node 18+
./scripts/build_webui.sh            # compila e incorpora la web UI nel firmware
pio run -e display -t upload        # compila e flasha il display via USB
```

Se entrambe le schede sono collegate, indica la porta esplicitamente e verifica che sia il
display: `pio run -e display -t upload --upload-port <PORTA>`.

### Generare il binario condivisibile (per l'autore)

```bash
pio run -e display                  # genera .pio/build/display/*.bin
esptool.py --chip esp32s3 merge_bin -o display-merged.bin \
  --flash_mode qio --flash_freq 80m --flash_size 16MB \
  0x0      .pio/build/display/bootloader.bin \
  0x8000   .pio/build/display/partitions.bin \
  0xe000   docs/boot_app0.bin \
  0x10000  .pio/build/display/firmware.bin
```

Flashare quel file da riga di comando (in alternativa al browser):

```bash
esptool.py --chip esp32s3 --port <PORTA> --baud 921600 write_flash 0x0 display-merged.bin
```

> 📦 *Opzionale — includere anche i profili caffè:* esegui `pio run -e display -t buildfs`,
> poi aggiungi `0xc90000 .pio/build/display/littlefs.bin` al comando `merge_bin`. Questo
> sovrascrive i profili/impostazioni salvati del destinatario, quindi omettilo se vuole
> mantenere i propri.

### Tornare al firmware ufficiale

Flasha il firmware ufficiale del display GaggiMate da **<https://gaggimate.eu/>** (il loro
flasher web). Poiché questo fork modifica solo l'app del display — nulla nel bootloader,
nella tabella delle partizioni o nella sicurezza della flash — la build ufficiale ripristina
completamente il dispositivo.
