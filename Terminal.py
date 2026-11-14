try:
    from Utils import *
except ModuleNotFoundError:
    try:
        from .Utils import *
    except ModuleNotFoundError:
        print("No Utils")
        import sys
        sys.exit()

try:
    from gi.repository import Vte
except:
    Vte = False

try:
    from gi.repository import GtkSource
except:
    GtkSource = False

class Window(DataWindow):
    view = GObject.Property(type=DataTabView)
    toolbar = GObject.Property(type=Adw.ToolbarView)
    context_tab = GObject.Property(type=Adw.TabPage)
    fullscreen = GObject.Property(type=bool, default=False)
    properties = ["fullscreen"]

    def __init__(self, data=None, tabs=None):
        tabs = tabs or []
        super().__init__(data)
        self.view = TabView(focusable=True)
        for i in (Adw.TabViewShortcuts.CONTROL_HOME, Adw.TabViewShortcuts.CONTROL_END, Adw.TabViewShortcuts.CONTROL_SHIFT_HOME, Adw.TabViewShortcuts.CONTROL_SHIFT_END): self.view.remove_shortcuts(i)
        self.toolbar = Adw.ToolbarView(content=self.view)
        box = Gtk.Box(css_name="main-header")
        a = {"New Window": "new-window", "New File": "new-file", "Open Files": "win.open-files", "Preferences": "preferences"}
        if not GtkSource:
            del a["New File"]
            del a["Open Files"]
        m = Menu({"!a": Menu(a), "!b": App.default.default_menu})
        new_tab = Button(css_classes=("flat",), callback=Tab.create, icon_name="tab-new", tooltip_text="New Tab", valign=Gtk.Align.CENTER)
        tab_button = Adw.TabButton(view=self.view.get_child(), valign=Gtk.Align.CENTER)
        tab_button.connect("clicked", self.__class__.tab_button_clicked)
        tab_button.get_first_child().add_css_class("flat")
        new_tab.bind_property("visible", tab_button, "visible", SYNC_BIND | INVERT_BIND)
        for i in (new_tab, tab_button, Adw.TabBar(view=self.view.get_child(), autohide=False), Button(t=Gtk.MenuButton, menu_model=m, icon_name="open-menu", tooltip_text="Menu")):
            if isinstance(i, Gtk.Button) or isinstance(i, Gtk.MenuButton):
                i.add_css_class("flat")
                i.set_valign(Gtk.Align.CENTER)
            box.append(i)
        self.toolbar.add_top_bar(box)
        overview = Adw.TabOverview(child=self.toolbar, enable_new_tab=True, view=self.view.get_child())
        overview.connect("create-tab", Tab.overview_create)
        self.view.set_menu_model(Tab.context_menu)
        self.view.connect("create-window", self.__class__.create)
        self.view.connect("setup-menu", Tab.setup_menu)
        self.view.connect("close-page", Tab.operation)
        self.breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.new_length(Adw.BreakpointConditionLengthType.MAX_WIDTH, 700, Adw.LengthUnit.PX))
        for i in ("apply", "unapply"): self.breakpoint.connect(i, self.update_css_size)
        self.breakpoint.add_setter(tab_button, "visible", True)
        self.add_breakpoint(self.breakpoint)
        self.set_content(overview)
        ToolbarFullscreen(self.toolbar)
        for i in ("fullscreen",):
            self.add_stateful_actions((i, get_variant(getattr(self, i.replace("-", "_")))))
            self.bind_property(i, self.lookup_action(i), "state", SYNC_BIND, variant_bind, unpack_bind)
        self.connect("notify::fullscreen", self.change_fullscreen)
        self.change_fullscreen()
        self.add_actions(("tab-context-set-title", Tab.action))
        if GtkSource: self.add_actions(("open-files", self.__class__.open_files))
        for i in self.view.restore(Tab): Tab.create(command=i["Command"], title=i["Title"])
        for i in tabs: Tab.create(command=i)
        if not self.view.get_selected_page(): Tab.create()
        self.present()

    @staticmethod
    def open_files(a, p, self): Gtk.FileDialog(filters=FILE_FILTER).open_multiple(None, None, self.__class__.do_open_files, self)

    @staticmethod
    def do_open_files(a, r, self):
        try:
            files = a.open_multiple_finish(r)
        except: return
        for i in files: Tab.create(view=self.view, command=i.get_uri())

    @staticmethod
    def on_key_pressed(e, v, kc, s):
        self = e.get_widget()
        if v == Gdk.KEY_F11: self.lookup_action("fullscreen").activate()
        if Gdk.ModifierType.CONTROL_MASK in s and (v == Gdk.KEY_O or v == Gdk.KEY_o and Gdk.ModifierType.SHIFT_MASK in s): self.get_content().set_open(not self.get_content().get_open())

    @staticmethod
    def tab_button_clicked(b):
        if not b.get_view().get_n_pages(): Tab.create(view=b.get_view())
        b.get_view().get_ancestor(Adw.TabOverview).set_open(not b.get_view().get_ancestor(Adw.TabOverview).get_open())

    @staticmethod
    def create(*_): return Window().view

    @staticmethod
    def on_click(e, *args):
        self = e.get_widget().get_root()
        if isinstance(e, Gtk.GestureClick):
            n, x, y, signal = args
        else:
            x, y, signal = args
        if signal == "released": return
        b = e.get_current_button()
        w = self.pick(x, y, Gtk.PickFlags.DEFAULT)

    def update_css_size(self, b):
        if not self.get_current_breakpoint(): self.add_css_class("small")
        else: self.remove_css_class("small")

    @staticmethod
    def on_map(self): self.view.page_changed()

class Find(Gtk.Revealer):
    find = GObject.Property(type=Gtk.SearchEntry)
    replace = GObject.Property(type=Gtk.Entry)
    def __init__(self, widget):
        box = Gtk.Box(css_name="search", orientation=Gtk.Orientation.VERTICAL)
        super().__init__(css_name="find", transition_duration=300, halign=Gtk.Align.CENTER, child=box, valign=Gtk.Align.START)
        self.actions = Gio.SimpleActionGroup()
        self.insert_action_group(self.__class__.__name__.lower(), self.actions)
        for n, v in [("Regex", True), ("Whole Words", False), ("Case Sensitive", True), ("Replace All", False)]:
            variant = get_variant(v)
            a = Gio.SimpleAction.new_stateful(n.lower().replace(" ", "-"), None, variant)
            if n != "Replace All": a.connect("notify::state", self.__class__.changed, self)
            self.add_action(a)
        self.find = Gtk.SearchEntry(hexpand=True, placeholder_text="Find")
        self.find.connect("activate", self.__class__.find_activate)
        self.find.connect("search-changed", self.__class__.changed)
        b1, b2 = [Gtk.Box(css_classes=["dark-blur-background", "linked"], hexpand=True) for _ in range(2)]
        box.append(b1)
        for i in (Button(icon_name="go-previous", tooltip_text="Previous", callback=self.__class__.go), self.find, Button(t=Gtk.MenuButton, icon_name="emblem-system", tooltip_text="Options", menu_model=Menu(dict((i, f"find.{i.lower().replace(' ', '-')}") for i in ("Regex", "Whole Words", "Case Sensitive")))), Button(icon_name="go-next", tooltip_text="Next", callback=self.__class__.go)): b1.append(i)
        if View and isinstance(widget, View):
            self.replace = Gtk.Entry(hexpand=True, primary_icon_tooltip_text="Replace", primary_icon_name="edit-find-replace-symbolic", placeholder_text="Replace")
            for i in (self.replace,): b2.append(i)
            box.append(b2)
            self.lookup_action("replace-all").bind_property("state", self.replace, "secondary-icon-name", DEFAULT_BIND, self.__class__.icon_bind)
            self.replace.bind_property("secondary-icon-name", self.replace, "secondary-icon-tooltip-text", DEFAULT_BIND, self.__class__.icon_tooltip_bind)
            self.replace.connect("activate", self.__class__.do_replace)
            self.replace.connect("icon-press", self.__class__.icon_press)
            self.replace.bind_property("visible", b2, "visible", DEFAULT_BIND)
        self.bind_property("valign", self, "transition-type", DEFAULT_BIND, self.__class__.find_reveal_bind)
        self.connect("notify::root", self.__class__.root_changed)

    def add_action(self, action): self.actions.add_action(action)

    def lookup_action(self, name): return self.actions.lookup_action(name)

    @property
    def widget(self): return (self.get_ancestor(Terminal) if Terminal else False) or (self.get_ancestor(View) if View else False)

    @staticmethod
    def root_changed(self, *_):
        if hasattr(self.get_root(), "breakpoint"): self.get_root().breakpoint.add_setter(self, "valign", Gtk.Align.END)

    def stop(self):
        self.find.set_text("")
        self.set_reveal_child(False)

    @staticmethod
    def find_activate(s):
        self = s.get_ancestor(Find)
        if self: self.move(True)

    @staticmethod
    def icon_bind(b, v): return "edit-select" + ("-all" if v.unpack() else "") + "-symbolic"

    @staticmethod
    def icon_tooltip_bind(b, v): return "All" if v and "-all" in v else "Selected"

    @staticmethod
    def icon_press(s, b):
        self = s.get_ancestor(Find)
        if self and b == 0: self.do_replace()
        if b == 1: self.lookup_action("replace-all").set_state(get_variant(not self.lookup_action("replace-all").get_state().unpack()))

    def do_replace(self):
        self = self if isinstance(self, Find) else self.get_ancestor(Find) if isinstance(self, Gtk.Widget) else None
        if not self or not self.find.get_text() or not self.widget: return
        widget = self.widget
        if widget.context.get_regex_error(): return
        if widget.context.get_settings().get_property("regex-enabled"):
            if not GLib.Regex.check_replacement(self.replace.get_text())[0]: return Toast("Invalid Replacement")
        if self.lookup_action("replace-all").get_state().unpack(): widget.context.replace_all(self.replace.get_text(), -1)
        else:
            r = widget.get_buffer().get_selection_bounds()
            if not r: return self.move(True, self.__class__.try_replace, (widget, self.replace.get_text()))
            widget.context.replace(r[0], r[1], self.replace.get_text(), -1)

    @staticmethod
    def try_replace(a):
        view, t = a
        r = view.get_buffer().get_selection_bounds()
        if r: view.context.replace(r[0], r[1], t, -1)

    def move(self, v=False, func=False, data=None):
        widget = self.widget
        if not widget: return
        if Terminal and isinstance(widget, Terminal):
            if v: widget.vte.search_find_next()
            else: widget.vte.search_find_previous()
        if View and isinstance(widget, View) and not widget.context.get_regex_error():
            i = widget.get_buffer().get_selection_bounds()
            if i and v:
                i = i[-1]
            elif i:
                i = i[0]
            s = widget.get_buffer().get_start_iter()
            i = i or s
            (widget.context.forward_async if v else widget.context.backward_async)(i, None, self.__class__.move_finish, ("forward" if v else "backward", widget.source, func, data))

    @staticmethod
    def move_finish(a, b, data):
        move, view, func, d = data
        if move == "backward":
            v = a.backward_finish(b)
        else:
            v = a.forward_finish(b)
        if v[0]:
            view.get_buffer().select_range(v[1], v[2])
            i = view.get_buffer().get_insert()
            view.scroll_mark_onscreen(i)
            if func: func(d)
        return 0

    @staticmethod
    def go(b):
        self = b.get_ancestor(Find)
        if not self: return
        self.move(b.get_tooltip_text() == "Next")

    def changed(self, b=None, c=None):
        if isinstance(self, Gtk.Widget):
            self = self.get_ancestor(Find)
        if not isinstance(self, Find):
            self = c
        if not isinstance(self, Find) or not self.widget: return
        find = self.find.get_text()
        widget = self.widget
        if Terminal and isinstance(widget, Terminal):
            if not self.lookup_action("regex").get_state().unpack():
                find = GLib.Regex.escape_string(find, -1)
            flags = VTE_PCRE2_MULTILINE
            if not self.lookup_action("case-sensitive").get_state().unpack():
                flags = flags | VTE_PCRE2_CASELESS
            if self.lookup_action("whole-words").get_state().unpack():
                find = fr"\b{find}\b"
            if find:
                r = None
            else:
                r = Vte.Regex.new_for_search(find, -1, flags)
            widget.vte.search_set_regex(r, 0)
            widget.vte.search_set_wrap_around(True)
            self.move(True)
        if View and isinstance(widget, View):
            widget.context.get_settings().set_property("regex-enabled", self.lookup_action("regex").get_state().unpack())
            widget.context.get_settings().set_property("case-sensitive", self.lookup_action("case-sensitive").get_state().unpack())
            widget.context.get_settings().set_property("at-word-boundaries", self.lookup_action("whole-words").get_state().unpack())
            if not widget.context.get_settings().get_property("regex-enabled"):
                find = GtkSource.utils_unescape_search_text(find)
            old = widget.context.get_settings().get_property("search-text")
            widget.context.get_settings().set_property("search-text", find)
            if widget.context.get_regex_error(): Toast("Invalid Search")
            elif old != find: self.move(True)

    @staticmethod
    def find_reveal_bind(b, v): return Gtk.RevealerTransitionType.SLIDE_DOWN if v == Gtk.Align.START else Gtk.RevealerTransitionType.SLIDE_UP

class TabView(DataTabView):
    def page_changed(self):
        if not self.get_mapped() or not self.current: return
        tab = self.current
        if not tab.get_child():
            if GtkSource and (not tab.command or tab.command.startswith("file://")): View(tab.command, tab)
            elif Vte: tab.set_child(Terminal(tab.command))
        tab.get_child().grab_focus()

class Tab(DataWindowTab):
    context_menu = Menu({"Set Title": "win.tab-context-set-title"})

    command = GObject.Property(type=str, default="")
    title = GObject.Property(type=str, default="")
    find = GObject.Property(type=str)
    replace = GObject.Property(type=str)
    properties = ["command", "title"]
    closed = []

    @classproperty
    def current(*_): return Window.current.view.current if Window.current else None

    def __init__(self, command=False, view=None, title=False):
        view = view or App.default.get_active_window().view
        command = command if isinstance(command, str) else App.default.PREFERENCES.new_tab_command
        super().__init__(view=view, command=command, title=title or "", css_name="tab")
        self.bind_property("title", self.tab, "title", DEFAULT_BIND, self.__class__.title_bind)

    @staticmethod
    def title_bind(b, v):
        if v: return v
        self = b.get_property("source")
        return basename(uri_decode(self.command)) if self.command.startswith("file://") else "Terminal" if self.command else "New File"

    @staticmethod
    def overview_create(*_): return Tab.create().tab

    @staticmethod
    def create(*_, view=False, command=False, title=False): return Tab(view=view, command=command, title=title)

    @staticmethod
    def new_file(*_): return Tab.create(command="")

    @staticmethod
    def setup_menu(v, t): v.get_root().set_property("context-tab", t)

    @staticmethod
    def action(a, p, window):
        tab = window.context_tab if "context" in a.get_name() else window.view.get_selected_page()
        if "set-title" in a.get_name():
            d = EntryPrompt(callback=Tab.do_change_title, heading="Set Tab Title")
            d.tab = tab.get_child()
            d.present()

    @staticmethod
    def do_change_title(d):
        tab = d.tab
        del d.tab
        tab.title = d.get_extra_child().get_text()

    @staticmethod
    def get_all():
        tabs = []
        for w in App.default.get_windows():
            if not isinstance(w, Window): continue
            for i in w.view: tabs.append(i)
        return tabs

    @staticmethod
    def operation(a, b=False, t=False):
        view = a.get_parent() if isinstance(a, Adw.TabView) else App.default.get_active_window().view
        if not t:
            t = b if isinstance(b, Adw.TabPage) else view.get_root().context_tab if "context" in a.get_name() else view.get_selected_page()
            t = t.get_child()
        if not t: return
        view = t.get_ancestor(TabView)
        if isinstance(a, TabView) or isinstance(a, Gio.SimpleAction) and "close-tab" in a.get_name():
            if view: view.close_page(t.tab) if isinstance(a, Gio.SimpleAction) else None
            Tab.closed.append(t.command)
            App.default.lookup_action("reopen-tab").set_enabled(bool(Tab.closed))
            if getattr(t.get_child(), "pid", 0) > 10: GLib.spawn_command_line_async(f"kill -s 9 {t.get_child().pid}")

    @staticmethod
    def reopen(*_):
        if Tab.closed:
            p = Tab.closed.pop(-1)
            while p in Tab.closed: Tab.closed.remove(p)
            Tab.create(command=p)
            App.default.lookup_action("reopen-tab").set_enabled(bool(Tab.closed))

class Color(ListObject):
    rgba = GObject.Property(type=RGBA)
    title = GObject.Property(type=str)

    @staticmethod
    def changed(self, p=None):
        a = [i.rgba.to_string() for i in App.default.PREFERENCES.colors]
        b = (Settings["Vte Palette"] or "#ffffff\n#1c1c1f\n#241f31\n#c01c28\n#2ec27e\n#f5c211\n#1e78e4\n#9841bb\n#0ab9dc\n#c0bfbc\n#5e5c64\n#ed333b\n#57e389\n#f8e45c\n#51a1ff\n#c061cb\n#4fd2fd\n#f6f5f4").split("\n")
        while len(a) > len(b): b.append("")
        for n, i in enumerate(a):
            b[n] = i
        Settings["Vte Palette"] = "\n".join(b)
        for i in Terminal.get_all():
            i.colors = App.default.PREFERENCES.colors

class ColorItem(ListItem):
    def __init__(self):
        p = {"valign": Gtk.Align.CENTER, "halign": Gtk.Align.CENTER, "overflow": Gtk.Overflow.HIDDEN}
        super().__init__(child=Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(), **p), **p)
        self.get_child().get_first_child().set_properties(**p)
        self.get_child().get_first_child().get_first_child().set_properties(**p)

    def bind(self):
        self.bindings.append(self.item.bind_property("rgba", self.get_child(), "rgba", SYNC_BIND))
        self.bindings.append(self.item.bind_property("title", self.get_child(), "tooltip-text", DEFAULT_BIND))

class Preferences(Adw.PreferencesDialog):
    new_tab_command = GObject.Property(type=str)
    cursor_shape = GObject.Property(type=str)
    show_line_numbers = GObject.Property(type=bool, default=True)
    highlight_current_line = GObject.Property(type=bool, default=True)
    vte_font = GObject.Property(type=Pango.FontDescription)
    colors = GObject.Property(type=List)
    style_scheme = (GObject.Property(type=GtkSource.StyleScheme) if GtkSource else None)
    source_font = GObject.Property(type=Pango.FontDescription)
    source_font_css =  GObject.Property(type=str)

    def __init__(self):
        super().__init__(content_width=600, content_height=600)
        if not APP_CSS in App.default.css:
            App.default.css = App.default.css + APP_CSS
        Settings.get_data()
        self.add_css_class("terminal-preferences")
        App.default.PREFERENCES = self
        if GtkSource:
            GtkSource.LanguageManager.get_default().prepend_search_path(Settings.data_folder.peek_path())
            GtkSource.StyleSchemeManager.get_default().prepend_search_path(Settings.data_folder.peek_path())
            GtkSource.StyleSchemeManager.get_default().force_rescan()
        general = Adw.PreferencesPage(title="General", icon_name="applications-development-symbolic")
        theme = Adw.PreferencesPage(title="Theme", icon_name="applications-graphics-symbolic")
        for i in (general, theme): self.add(i)
        if Vte:
            group = Adw.PreferencesGroup(title="Vte")
            new_tab_command = Adw.EntryRow(title="New Tab Command", text=Settings["New Tab Command"] or "")
            new_tab_command.bind_property("text", self, "new-tab-command", DEFAULT_BIND)
            new_tab_command.connect("changed", self.__class__.setting_changed)
            cursor_shape = Adw.ActionRow(title="Cursor Shape")
            g = Adw.ToggleGroup(name="Vte Cursor Shape", valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
            cursor_shape.add_suffix(g)
            for i in ["Block", "Vertical Bar", "Horizontal Bar"]: g.add(Adw.Toggle(label=i, name=i))
            g.set_active_name(Settings["Vte Cursor Shape"] or "Vertical Bar")
            g.bind_property("active-name", self, "cursor-shape", SYNC_BIND)
            g.connect("notify::active", self.__class__.setting_changed)
            for i in (new_tab_command, cursor_shape): group.add(i)
            general.add(group)

        if GtkSource:
            group = Adw.PreferencesGroup(title="Source")
            for i in ("Show Line Numbers", "Highlight Current Line"):
                i = Adw.SwitchRow(title=i)
                v = Settings[i.get_title()]
                if v != None: setattr(self, i.get_title().lower().replace(" ", "_"), v)
                self.bind_property(i.get_title().lower().replace(" ", "-"), i, "active", SYNC_BIND)
                i.connect("notify::active", self.__class__.setting_changed)
                group.add(i)
            general.add(group)

        if Vte:
            group = Adw.PreferencesGroup(title="Vte")
            font = FontRow(title="Font", font_desc=Pango.FontDescription.from_string(Settings["Vte Font"] or "Adwaita Mono 20"), name="Vte Font")
            font.bind_property("font-desc", self, "vte-font", SYNC_BIND)
            font.connect("notify::font-desc", self.__class__.setting_changed)
            size = Adw.ExpanderRow(title="Palette Size")
            g = Adw.ToggleGroup(valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
            for i in ["0", "8", "16", "232", "256"]: g.add(Adw.Toggle(label=i, name=i))
            g.set_active_name(str(Settings["Vte Palette Size"] or "16"))
            size.add_suffix(g)
            colors = Gtk.GridView(max_columns=10, min_columns=10, factory=ColorItem.factory, model=Gtk.NoSelection(), valign=Gtk.Align.START)
            colors.set_css_classes([])
            size.add_row(colors)
            colors.get_parent().add_css_class("color")
            self.bind_property("colors", colors.get_model(), "model", DEFAULT_BIND)
            g.bind_property("active-name", self, "colors", DEFAULT_BIND, self.__class__.palette_size_bind)
            for i in (font, size): group.add(i)
            theme.add(group)

        if GtkSource:
            group = Adw.PreferencesGroup(title="Source")
            b = GtkSource.StyleSchemeChooserButton(name="Source Style Scheme", valign=Gtk.Align.CENTER)
            b.bind_property("style-scheme", self, "style-scheme", SYNC_BIND)
            v = Settings["Source Style Scheme"] or "Adwaita-dark"
            if v in GtkSource.StyleSchemeManager.get_default().get_scheme_ids(): b.set_style_scheme(GtkSource.StyleSchemeManager.get_default().get_scheme(v))
            b.connect("notify::style-scheme", self.__class__.setting_changed)
            font = FontRow(title="Font", font_desc=Pango.FontDescription.from_string(Settings["Source Font"] or "Adwaita Mono 20"), name="Source Font")
            font.bind_property("font-desc", self, "source-font", SYNC_BIND)
            font.connect("notify::font-desc", self.__class__.setting_changed)
            group.add(font)
            self.bind_property("source-font-css", CSS(), "css", SYNC_BIND)
            self.__class__.setting_changed(font)
            for i in (b, ):
                r = Adw.ActionRow(title=i.get_name().split("Source ", 1)[-1])
                r.add_suffix(i)
                group.add(r)
            theme.add(group)

    @staticmethod
    def palette_size_bind(b, v):
        l = List(Color)
        default_colors = (Settings["Vte Palette"] or "#ffffff\n#1c1c1f\n#241f31\n#c01c28\n#2ec27e\n#f5c211\n#1e78e4\n#9841bb\n#0ab9dc\n#c0bfbc\n#5e5c64\n#ed333b\n#57e389\n#f8e45c\n#51a1ff\n#c061cb\n#4fd2fd\n#f6f5f4").split("\n")
        l.append(Color(title="Foreground", rgba=RGBA(default_colors[0])))
        l.append(Color(title="Background", rgba=RGBA(default_colors[1])))
        default_colors = default_colors[2:]
        for n in range(int(v) if v.isdigit() else 0): l.append(Color(rgba=RGBA(default_colors[n] if len(default_colors) > n else ""), title=str(n + 1)))
        return l

    @staticmethod
    def setting_changed(w, p=None):
        if isinstance(w, Adw.ToggleGroup):
            Settings[w.get_name()] = w.get_active_name()
        if isinstance(w, Adw.EntryRow):
            Settings[w.get_title()] = w.get_text()
        if isinstance(w, FontRow):
            font = w.get_font_desc()
            Settings[w.get_name()] = font.to_string()
            if w.get_name() == "Source Font":
                App.default.PREFERENCES.source_font_css = "textview { font-family: " + font.get_family() + "; font-size: " + str(int(font.get_size() / Pango.SCALE)) + "pt; }"
        if isinstance(w, GtkSource.StyleSchemeChooserButton):
            Settings[w.get_name()] = w.get_style_scheme().get_id()

    @staticmethod
    def show(*_):
        if App.default.PREFERENCES.get_mapped(): App.default.PREFERENCES.close()
        App.default.PREFERENCES.present()

class View(Gtk.Overlay):
    find = GObject.Property(type=Find)
    file = GObject.Property(type=GObject.Object)
    source = GObject.Property(type=GObject.Object)
    context = GObject.Property(type=GObject.Object)
    cancel = GObject.Property(type=Gio.Cancellable)
    tab = GObject.Property(type=Tab)
    def __init__(self, uri, tab=None, **kwargs):
        super().__init__(css_name=self.__class__.__name__.lower())
        self.source = GtkSource.View(right_margin=0, left_margin=0, wrap_mode=Gtk.WrapMode.WORD_CHAR, auto_indent=True, indent_width=4, insert_spaces_instead_of_tabs=True, tab_width=4, smart_backspace=True, smart_home_end=GtkSource.SmartHomeEndType.ALWAYS)
        self.set_child(Gtk.ScrolledWindow(child=self.source))
        self.source.set_css_classes([])
        self.context = GtkSource.SearchContext.new(self.get_buffer())
        self.context.get_settings().set_property("wrap-around", True)
        self.tab = tab
        self.get_buffer().set_max_undo_levels(0)
        if self.tab: self.get_buffer().bind_property("loading", self.tab.tab, "loading", DEFAULT_BIND)
        self.get_buffer().set_implicit_trailing_newline(False)
        self.file = GtkSource.File.new()
        self.file.set_location(Gio.File.new_for_uri(uri) if uri else None)
        self.__class__.reload_file(self)
        self.add_css_class("terminal")
        self.source.connect("notify::show-line-numbers", self.__class__.change_margin)
        if not hasattr(App.default, "PREFERENCES"): Preferences()
        if hasattr(App.default, "PREFERENCES"):
            App.default.PREFERENCES.bind_property("style-scheme", self.get_buffer(), "style-scheme", DEFAULT_BIND)
            App.default.PREFERENCES.bind_property("show-line-numbers", self.source, "show-line-numbers", DEFAULT_BIND)
            App.default.PREFERENCES.bind_property("highlight-current-line", self.source, "highlight-current-line", DEFAULT_BIND)
        Window.controller_init(self)
        self.connect("map", self.__class__.on_map)
        self.find = Find(self)
        self.add_overlay(self.find)

    def grab_focus(self): return self.source.grab_focus()

    def get_buffer(self): return self.source.get_buffer()

    @staticmethod
    def on_key_pressed(e, v, kc, s):
        self = e.get_widget()
        if Gdk.ModifierType.CONTROL_MASK in s and v in (Gdk.KEY_n, Gdk.KEY_N):
            self.find.move(True)
            return True
        if Gdk.ModifierType.CONTROL_MASK in s and v in (Gdk.KEY_p, Gdk.KEY_P):
            self.find.move()
            return True
        if Gdk.ModifierType.CONTROL_MASK in s and v in (Gdk.KEY_f, Gdk.KEY_F):
            self.find.set_reveal_child(not (self.get_root() and self.get_root().get_focus() and self.get_root().get_focus().get_ancestor(Find)))
            if self.find.get_reveal_child():
                b = self.get_buffer().get_selection_bounds()
                if b:
                    t = self.get_buffer().get_text(b[0], b[1], True)
                    if self.find.lookup_action("regex").get_state().unpack():
                        t = GLib.Regex.escape_string(t, -1)
                    self.find.find.set_text(t)
                    self.find.find.select_region(0, -1)
                self.find.find.grab_focus()
            else:
                self.find.stop()
                self.source.grab_focus()
            return True
        if Gdk.ModifierType.CONTROL_MASK in s and v in (Gdk.KEY_h, Gdk.KEY_H):
            self.find.do_replace()
            return True
        if v == Gdk.KEY_Escape and self.find.get_mapped():
            self.find.stop()
            self.source.grab_focus()
            return True
        file = self.file
        if Gdk.ModifierType.CONTROL_MASK in s and v in (Gdk.KEY_s, Gdk.KEY_S):
            if v == Gdk.KEY_S or not file.get_location(): Gtk.FileDialog(initial_name="New File").save(None, None, self.__class__.do_save_dialog, self)
            else: self.save()

    @staticmethod
    def on_scroll(e, x, y):
        if Gdk.ModifierType.CONTROL_MASK in e.get_current_event_state():
            f = App.default.PREFERENCES.source_font
            f.set_size(f.get_size() + (-y * 2000))
            App.default.PREFERENCES.source_font = f
            return True

    def on_map(self, *_):
        self.file.check_file_on_disk()
        if self.file.is_externally_modified():
            d = Prompt(heading="Reload File?", body="File has changed on disk", callback=self.__class__.reload_file)
            d.view = self
            d.present(self.get_root())

    @staticmethod
    def reload_file(d):
        self = d if View and isinstance(d, View) else d.view
        if not self.tab:
            self.tab = self.get_ancestor(Tab)
        if self.tab: self.tab.set_child(Adw.Spinner())
        if hasattr(d, "view"):
            del d.view
        if self.file.get_location():
            l = GtkSource.LanguageManager.get_default().guess_language(self.file.get_location().get_basename())
            if l: self.get_buffer().set_language(l)
            self.cancel = Gio.Cancellable.new()
            GtkSource.FileLoader.new(self.get_buffer(), self.file).load_async(GLib.PRIORITY_DEFAULT, self.cancel, None, None, self.__class__.do_load_finish, self)
        else: self.__class__.do_load_finish(self=self)

    @staticmethod
    def do_load_finish(a=None, r=None, self=None):
        if a and r:
            try: a.load_finish(r)
            except Exception as e:
                if "No such file" in str(e): Toast(f"{self.file.get_location()} doesn't exist")
                else: Toast(e)
        if self.tab: self.tab.set_child(self)
        self.tab = None

    @staticmethod
    def change_margin(source, p=None): source.set_left_margin(10 if source.get_property("show-line-numbers") else 0)

    def save(self): GtkSource.FileSaver.new(self.get_buffer(), self.file).save_async(GLib.PRIORITY_DEFAULT, self.cancel, None, None, self.__class__.do_save_finish, self)

    @staticmethod
    def do_save_dialog(a, r, self):
        try:
            f = a.save_finish(r)
        except: return
        self.file.set_location(f)
        tab = self.get_ancestor(Tab)
        if tab:
            tab.command = f.get_uri()
            tab.title = ""
        self.save()

    @staticmethod
    def do_save_finish(a, r, self):
        l = self.file.get_location()
        try:
            result = a.save_finish(r)
            Toast("Saved File" if result else "Couldn't Save File", timeout=1 if result else 0)
        except Exception as e:
            if "externally modified" in str(e):
                d = Prompt(heading="Overwrite File?", body="This file has been externally modified", callback=self.__class__.overwrite_file)
                d.view = self
                d.present(self.get_root())
            else: Toast(f"{e} {l.get_uri()}", timeout=0)

    @staticmethod
    def overwrite_file(d):
        self = d.view
        del d.view
        l = self.file.get_location()
        self.file = GtkSource.File.new()
        self.file.set_location(l)
        self.save()

if not GtkSource:
    View = False

class Terminal(Gtk.Overlay):
    find = GObject.Property(type=Find)
    vte = GObject.Property(type=GObject.Object)

    @GObject.Property(type=List)
    def colors(self): return getattr(self, "_colors", None)

    @colors.setter
    def colors(self, value):
        setattr(self, "_colors", value)
        if self.colors:
            l = [i.rgba.copy() if i.rgba else Gdk.RGBA() for i in self.colors]
            self.vte.set_colors(l[0], l[1], l[2:])

    def __init__(self, command):
        super().__init__(css_name=self.__class__.__name__.lower())
        self.add_css_class("terminal")
        self.vte = Vte.Terminal(scrollback_lines=1024, allow_hyperlink=True, enable_sixel=True)
        self.set_child(Gtk.ScrolledWindow(child=self.vte))
        Window.controller_init(self)
        if not hasattr(App.default, "PREFERENCES"): Preferences()
        if hasattr(App.default, "PREFERENCES"):
            self.colors = App.default.PREFERENCES.colors
            App.default.PREFERENCES.bind_property("vte-font", self.vte, "font-desc", SYNC_BIND)
            App.default.PREFERENCES.bind_property("cursor-shape", self.vte, "cursor-shape", SYNC_BIND, self.__class__.shape_bind)
        self.vte.connect("child-exited", self.__class__.child_exited)
        self.vte.spawn_async(Vte.PtyFlags.DEFAULT, None, GLib.shell_parse_argv(command)[-1], None, GLib.SpawnFlags.DEFAULT, None, None, GLib.MAXINT, None, self.__class__.finish_spawn, None)
        self.find = Find(self)
        self.add_overlay(self.find)

    def grab_focus(self): return self.vte.grab_focus()

    @staticmethod
    def shape_bind(b, v): return Vte.CursorShape.IBEAM if v == "Vertical Bar" else Vte.CursorShape.UNDERLINE if v == "Horizontal Bar" else 0

    @staticmethod
    def finish_spawn(v, p, e=None, d=None):
        self = v.get_ancestor(Terminal)
        self.pid = p

    @staticmethod
    def child_exited(v, s):
        self = v.get_ancestor(Terminal)
        if hasattr(self, "pid"):
            del self.pid
            if self.get_ancestor(Tab): Tab.operation(App.default.lookup_action("close-tab"), b=None, t=self.get_ancestor(Tab))

    @staticmethod
    def get_all():
        l = []
        for i in Tab.get_all():
            if isinstance(i.get_child(), Terminal): l.append(i.get_child())
        return l

    @staticmethod
    def on_scroll(e, x, y):
        if Gdk.ModifierType.CONTROL_MASK in e.get_current_event_state():
            f = App.default.PREFERENCES.vte_font
            f.set_size(f.get_size() + (-y * 2000))
            App.default.PREFERENCES.vte_font = f
            return True

    @staticmethod
    def on_key_pressed(e, v, kc, s):
        self = e.get_widget()
        t = self.get_ancestor(Tab)
        if t and t.command == App.default.PREFERENCES.new_tab_command:
            if Gdk.ModifierType.CONTROL_MASK in s and v == Gdk.KEY_F:
                self.find.set_reveal_child(not self.find.get_reveal_child())
                return True
            if Gdk.ModifierType.CONTROL_MASK in s and v == Gdk.KEY_V:
                self.vte.paste_clipboard()
                return True
            if Gdk.ModifierType.CONTROL_MASK in s and v == Gdk.KEY_C:
                self.get_root().set_focus(t)
                self.vte.copy_clipboard_format(Vte.Format.TEXT)
                GLib.timeout_add(200, self.get_root().set_focus, self.vte)
                return True

if not Vte:
    Terminal = False

def handle_command(a, ar):
    ar = ar.get_arguments()
    if len(ar) >= 1:
        ar = ar[1:]
    if App.default.get_active_window(): App.default.get_active_window().present()
    elif not Window.current: Window.restore(new=True)
    for i in ar: Tab.create(command=i)
    return 0

INFO = {
    "ID": "io.github.kirukomaru11.Terminal",
    "Developer": "きるこ丸11号",
    "Comment": "Terminal and file editing",
    "Issue URL": "https://github.com/kirukomaru11/Terminal/issues",
    "Website": "https://github.com/kirukomaru11/Terminal",
    "Keywords": ["Edit", "Text"],
    "Categories": ["System", "TerminalEmulator"],
    "Branding": ["#7b959a", "#b5c3c6"],
    "MimeTypes": [i for i in Gio.content_types_get_registered() if i.startswith("text/")]
}

for i in "text/plain;text/x-chdr;text/x-csrc;text/x-c++hdr;text/x-c++src;text/x-java;text/x-dsrc;text/x-pascal;text/x-perl;text/x-python;application/x-php;application/x-httpd-php3;application/x-httpd-php4;application/x-httpd-php5;application/xml;text/html;text/css;text/x-sql;text/x-diff".split(";"):
    if not i in INFO["MimeTypes"]: INFO["MimeTypes"].append(i)

APP_CSS = """
view.terminal textview,
view.terminal textview border,
view.terminal textview border gutter,
view.terminal textview text { background: none; }

terminal.terminal vte-terminal { padding: 6px; }

view.terminal find,
terminal.terminal find { margin-left: 5px; margin-right: 5px; margin-bottom: 5px; }
.fullscreen view.terminal find,
.fullscreen terminal.terminal find { margin-top: 5px; }
view.terminal find > search,
terminal.terminal find > search { border-spacing: 5px; }
view.terminal find > search > box,
terminal.terminal find > search > box { border-radius: 9px; }

.terminal-window main-header { padding: 0px 5px; }
.terminal-window main-header > menubutton { margin-left: 5px; }
.terminal-window tabbar > revealer > box { padding: 0px; }

.terminal-preferences row.color gridview { border-spacing: 0px 12px; padding: 6px 0px; }
.terminal-preferences row.color gridview child,
.terminal-preferences row.color gridview child widget { padding: 0px; border-radius: 100%; }
"""

class Settings(metaclass=DictSettingMeta):
    def get_data():
        if hasattr(Settings, "data"):
            try: Settings.data.execute("SELECT 1").close()
            except Exception as e:
                if hasattr(Settings, "data"):
                    Settings.data.close()
                    del Settings.data
        if not hasattr(Settings, "data"):
            if App.default.get_application_id().endswith("Terminal"):
                Settings.data = App.default.data
                Settings.data_folder = App.default.data_folder
            else:
                flatpak_data = Path(Path(Path("/run/host/root" if FLATPAK_ID else "/", HOME), ".var", "app", INFO["ID"], "data"), "data")
                Settings.data = Data(flatpak_data if exists(flatpak_data) else Path(DATA, "Terminal", "data"), DATA_INIT, readonly=True)
                Settings.data_folder = Gio.File.new_for_path(Settings.data.path).get_parent()
        return Settings.data

DATA_INIT = (Settings, Tab, Window)

FILE_FILTER = Gio.ListStore.new(Gtk.FileFilter)
FILE_FILTER.append(Gtk.FileFilter(name="Text", mime_types=["text/*"]))

VTE_PCRE2_UCP = 0x00020000
VTE_PCRE2_MULTILINE = 0x00000400
VTE_PCRE2_CASELESS = 0x00000008

SHORTCUTS = {
    "Tabs": {
        "New": "app.new-tab",
        "Close": "app.close-tab",
        "Reopen Closed": "app.reopen-tab",
        "Overview": "<primary><shift>o",
        **Adw.TabView.shortcuts
    },
    "Terminal": {
        "Find": "<primary><shift>f",
        "Copy": "<primary><shift>c",
        "Paste": "<primary><shift>v",
    },
    "Source": {
        "Find": "<primary>f",
        "Find Next": "<primary>n",
        "Find Previous": "<primary>p",
        "Stop Find": "Escape",
        "Replace": "<primary>h",
        "Save": "<primary>s"
    },
    "Window": {
        "Fullscreen": "F11",
        "New Window": "app.new-window",
        "New File": "app.new-file",
        "Preferences": "app.preferences"
    }
}

ACTIONS = [("reopen-tab", Tab.reopen, "<primary><shift>t"),
    ("close-tab", Tab.operation, "<primary>w"),
    ("new-tab", Tab.create, "<primary>t"),
    ("new-window", Window.create, "<primary><shift>w"),
    ("preferences", Preferences.show, "<primary><shift>p")]

if not Vte:
    del SHORTCUTS["Terminal"]

if GtkSource:
    ACTIONS.append(("new-file", Tab.new_file, "<primary><shift>n"))
else:
    del SHORTCUTS["Source"]
    del SHORTCUTS["Window"]["New File"]

def main():
    if GtkSource: GtkSource.init()
    flags = Gio.ApplicationFlags.HANDLES_COMMAND_LINE | Gio.ApplicationFlags.NON_UNIQUE if GLib.getenv("TEST") else None
    App(shortcuts=SHORTCUTS,
        data=DATA_INIT,
        command_line=handle_command,
        actions=ACTIONS,
        flags=flags,
        info=INFO)
    App.default.lookup_action("reopen-tab").set_enabled(False)
    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
    if GtkSource: App.default.set_accels_for_action("win.open-files", ["<primary>o"])
    Preferences()
    App.default.main()

if __name__ == "__main__": main()