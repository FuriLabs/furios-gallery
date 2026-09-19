PREFIX ?= /usr
LIBDIR = $(PREFIX)/lib
BINDIR = $(PREFIX)/bin
LIBEXECDIR = $(PREFIX)/libexec
DATADIR = $(PREFIX)/share
SYSTEMDUSERDIR = $(LIBDIR)/systemd/user

INSTALL_DIR = $(LIBDIR)/furios-gallery
DESKTOP_DIR = $(DATADIR)/applications
ICON_DIR = $(DATADIR)/icons/hicolor/scalable/apps

.PHONY: all install uninstall

all:
	@echo "Run 'make install' to install the files."

install:
	install -d $(DESTDIR)$(INSTALL_DIR)
	install -d $(DESTDIR)$(BINDIR)
	install -d $(DESTDIR)$(LIBEXECDIR)
	install -d $(DESTDIR)$(DESKTOP_DIR)
	install -d $(DESTDIR)$(ICON_DIR)
	install -d $(DESTDIR)$(SYSTEMDUSERDIR)
	install -d $(DESTDIR)$(SYSTEMDUSERDIR)/gnome-session.target.wants

	cp -r furios_gallery $(DESTDIR)$(INSTALL_DIR)/

	install -m 755 main.py $(DESTDIR)$(INSTALL_DIR)/
	install -m 755 furios-gallery-daemon/gallery_daemon.py $(DESTDIR)$(INSTALL_DIR)/

	install -m 644 data/io.furios.Gallery.desktop $(DESTDIR)$(DESKTOP_DIR)/
	install -m 644 data/io.furios.Gallery.svg $(DESTDIR)$(ICON_DIR)/

	install -m 644 data/furios-gallery-daemon.service $(DESTDIR)$(SYSTEMDUSERDIR)/

	ln -sf ../lib/furios-gallery/main.py $(DESTDIR)$(BINDIR)/io.furios.Gallery
	ln -sf ../lib/furios-gallery/gallery_daemon.py $(DESTDIR)$(LIBEXECDIR)/furios-gallery-daemon

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/io.furios.Gallery
	rm -f $(DESTDIR)$(LIBEXECDIR)/furios-gallery-daemon

	rm -rf $(DESTDIR)$(INSTALL_DIR)
	rm -f $(DESTDIR)$(DESKTOP_DIR)/io.furios.Gallery.desktop
	rm -f $(DESTDIR)$(ICON_DIR)/io.furios.Gallery.svg
	rm -f $(DESTDIR)$(SYSTEMDUSERDIR)/furios-gallery-daemon.service
