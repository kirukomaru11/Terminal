try:
    from Utils import *
except ModuleNotFoundError:
    try:
        from .Utils import *
    except ModuleNotFoundError:
        print("No Utils")
        exit()

try:
    from gi.repository import Vte
except:
    Vte = False

try:
    from gi.repository import GtkSource
except:
    GtkSource = False

class Window(Window):
    __gtype_name__ = "Window"

    view = GObject.Property(type=Adw.TabView)
    toolbar = GObject.Property(type=Adw.ToolbarView)
    find = GObject.Property(type=Gtk.Widget)
    context_tab = GObject.Property(type=Adw.TabPage)

    def __init__(self, _id=None, tabs=None):
        tabs = tabs or []
        super().__init__()
        self.find = Find()
        if not _id: App.default.data.set_default(table="Windows", conditions="ID = ?", conds=(self.get_id(),), names=("ID", ), values=(self.get_id(),))
        elif self.get_id() != _id: App.default.data.update(table="Windows", column="ID", value=self.get_id(), conditions="ID = ?", conds=(_id,))
        self.view = Adw.TabView(focusable=True)
        for i in (Adw.TabViewShortcuts.CONTROL_HOME, Adw.TabViewShortcuts.CONTROL_END, Adw.TabViewShortcuts.CONTROL_SHIFT_HOME, Adw.TabViewShortcuts.CONTROL_SHIFT_END): self.view.remove_shortcuts(i)
        overlay = Gtk.Overlay(child=self.view)
        overlay.add_overlay(self.find)
        self.toolbar = Adw.ToolbarView(content=overlay)
        box = Gtk.Box(css_name="main-header")
        a = {"New Window": "new-window", "New File": "new-file", "Open Files": "win.open-files", "Preferences": "preferences"}
        if not GtkSource:
            del a["New File"]
            del a["Open Files"]
        m = Menu({"!a": Menu(a), "!b": App.default.default_menu})
        new_tab = Button(css_classes=("flat",), callback=Tab.create, icon_name="tab-new", tooltip_text="New Tab", valign=Gtk.Align.CENTER)
        tab_button = Adw.TabButton(view=self.view, valign=Gtk.Align.CENTER)
        tab_button.connect("clicked", self.__class__.tab_button_clicked)
        tab_button.get_first_child().add_css_class("flat")
        new_tab.bind_property("visible", tab_button, "visible", INVERT_BIND)
        for i in (new_tab, tab_button, Adw.TabBar(view=self.view, autohide=False), Button(t=Gtk.ToggleButton, tooltip_text="Search", icon_name="edit-find", bindings=[(None, "active", self.find, "reveal-child", SYNC_BIND)]), Button(t=Gtk.MenuButton, menu_model=m, icon_name="open-menu", tooltip_text="Menu")):
            if isinstance(i, Gtk.Button) or isinstance(i, Gtk.MenuButton):
                i.add_css_class("flat")
                i.set_valign(Gtk.Align.CENTER)
            box.append(i)
        self.toolbar.add_top_bar(box)
        for i in ("Default Width", "Default Height"): App.default.data.persist_action(self, i, 1, "Windows", i, "ID = ?", (self.get_id(),)).bind_property("state", self, i.lower().replace(" ", "-"), SYNC_BIND, unpack_bind, variant_bind)
        App.default.data.persist_action(self, "Maximized", False, "Windows", "Maximized", "ID = ?", (self.get_id(),)).bind_property("state", self, "maximized", SYNC_BIND, unpack_bind, variant_bind)
        App.default.data.persist_action(self, "Fullscreen", False, "Windows", "Fullscreen", "ID = ?", (self.get_id(),)).connect("notify::state", self.change_fullscreen)
        for i in App.default.data.read(table="Tabs", conditions="Window = ?", conds=(self.get_id(),), return_dict=True, force_tuple=True): Tab.create(command=i["Command"], title=i["Title"])
        for i in tabs: Tab.create(command=i)
        if not self.view.get_selected_page(): Tab.create()
        overview = Adw.TabOverview(child=self.toolbar, enable_new_tab=True, view=self.view)
        overview.connect("create-tab", Tab.overview_create)
        self.view.set_menu_model(Tab.context_menu)
        self.view.connect("notify::selected-page", Tab.changed)
        self.view.connect("notify::n-pages", Tab.idle_save_all)
        self.view.connect("page-reordered", Tab.idle_save_all)
        self.view.connect("create-window", self.__class__.create)
        self.view.connect("setup-menu", Tab.setup_menu)
        self.view.connect("close-page", Tab.operation)
        b = Adw.Breakpoint.new(Adw.BreakpointCondition.new_length(Adw.BreakpointConditionLengthType.MAX_WIDTH, 700, Adw.LengthUnit.PX))
        for i in ("apply", "unapply"): b.connect(i, self.update_css_size)
        b.add_setter(tab_button, "visible", True)
        b.add_setter(self.find, "valign", Gtk.Align.END)
        self.add_breakpoint(b)
        self.set_content(overview)
        ToolbarFullscreen(self.toolbar)
        self.change_fullscreen()
        self.present()
        self.add_actions(("tab-context-set-title", Tab.action))
        if GtkSource:
            self.add_actions(("open-files", self.__class__.open_files))
        if GtkSource or Vte:
            for n, v in [("Regex", True), ("Whole Words", False), ("Case Sensitive", True)]:
                variant = get_variant(v)
                a = Gio.SimpleAction.new_stateful(n.lower().replace(" ", "-"), None, variant)
                a.connect("notify::state", Find.state_changed, self.find)
                self.add_action(a)

    @staticmethod
    def open_files(a, p, self): Gtk.FileDialog(filters=FILE_FILTER).open_multiple(None, None, self.__class__.do_open_files, self)

    @staticmethod
    def do_open_files(a, r, self):
        try:
            files = a.open_multiple_finish(r)
        except: return
        for i in files: Tab.create(view=self.view, command=i.get_uri())

    def on_scroll(e, x, y):
        if Gdk.ModifierType.CONTROL_MASK in e.get_current_event_state():
            t = Tab.current
            if t and Vte and isinstance(t.get_child(), Terminal):
                f = App.default.PREFERENCES.vte_font
                f.set_size(f.get_size() + (-y * 2000))
                App.default.PREFERENCES.vte_font = f
                return True
            if t and GtkSource and isinstance(t.get_child(), View):
                f = App.default.PREFERENCES.source_font
                f.set_size(f.get_size() + (-y * 2000))
                App.default.PREFERENCES.source_font = f
                return True

    @staticmethod
    def on_key_pressed(e, v, kc, s):
        self = e.get_widget()
        if v == Gdk.KEY_F11: self.lookup_action("fullscreen").activate()
        if Gdk.ModifierType.CONTROL_MASK in s and (v == Gdk.KEY_O or v == Gdk.KEY_o and Gdk.ModifierType.SHIFT_MASK in s): self.get_content().set_open(not self.get_content().get_open())
        if not self.view.get_selected_page(): return
        t = self.view.get_selected_page().get_child()
        if Vte and isinstance(t.get_child(), Terminal) and t.command == App.default.PREFERENCES.new_tab_command or isinstance(t.get_child(), View):
            if isinstance(t.get_child(), Terminal):
                if Gdk.ModifierType.CONTROL_MASK in s and v == Gdk.KEY_F:
                    self.find.set_reveal_child(not self.find.get_reveal_child())
                    return True
                if Gdk.ModifierType.CONTROL_MASK in s and v == Gdk.KEY_V:
                    t.get_child().paste_clipboard()
                    return True
                if Gdk.ModifierType.CONTROL_MASK in s and v == Gdk.KEY_C:
                    self.set_focus(self.view)
                    t.get_child().copy_clipboard_format(Vte.Format.TEXT)
                    GLib.timeout_add(200, self.set_focus, t.get_child())
                    return True
        if GtkSource and isinstance(t.get_child(), View):
            view = t.get_child()
            if Gdk.ModifierType.CONTROL_MASK in s and v == Gdk.KEY_n:
                self.find.move(True)
                return True
            if Gdk.ModifierType.CONTROL_MASK in s and v == Gdk.KEY_p:
                self.find.move()
                return True
            if Gdk.ModifierType.CONTROL_MASK in s and v == Gdk.KEY_f:
                self.find.set_reveal_child(True)
                if self.find.get_reveal_child():
                    b = view.get_buffer().get_selection_bounds()
                    if b:
                        t = view.get_buffer().get_text(b[0], b[1], True)
                        if self.lookup_action("regex").get_state().unpack():
                            t = GLib.Regex.escape_string(t, -1)
                        self.find.find.set_text(t)
                    self.find.find.grab_focus()
                else:
                    self.find.stop()
                    view.grab_focus()
                return True
            if Gdk.ModifierType.CONTROL_MASK in s and v == Gdk.KEY_h:
                self.find.do_replace()
                return True
            if v == Gdk.KEY_Escape and self.find.get_mapped():
                self.find.stop()
                view.grab_focus()
                return True
            file = view.file
            if Gdk.ModifierType.CONTROL_MASK in s and v in (Gdk.KEY_S, Gdk.KEY_s):
                if v == Gdk.KEY_S or not file.get_location(): Gtk.FileDialog(initial_name="New File").save(None, None, view.__class__.do_save_dialog, view)
                else: view.save()

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
    def on_map(w): Tab.changed(w.view)

    @staticmethod
    def clipboard_read_text(cl, r):
        App.default.get_active_window().set_focus(App.default.get_active_window().view)
        v = App.default.get_active_window().view.get_selected_page().get_child().get_child()
        v.feed_child(cl.read_text_finish(r).encode("utf-8"))
        GLib.timeout_add(200, App.default.get_active_window().set_focus, v)

class Find(Gtk.Revealer):
    __gtype_name__ = "Find"
    find = GObject.Property(type=Gtk.SearchEntry)
    replace = GObject.Property(type=Gtk.Entry)
    changing = GObject.Property(type=bool, default=False)
    def __init__(self):
        box = Gtk.Box(css_name="search", orientation=Gtk.Orientation.VERTICAL)
        super().__init__(css_name="find", transition_duration=300, halign=Gtk.Align.CENTER, child=box, valign=Gtk.Align.START)
        self.find = Gtk.SearchEntry(hexpand=True, placeholder_text="Find")
        self.find.connect("activate", self.__class__.find_activate)
        self.find.connect("search-changed", self.__class__.changed)
        self.replace = Gtk.Entry(hexpand=True, primary_icon_tooltip_text="Replace", primary_icon_name="edit-find-replace-symbolic", placeholder_text="Replace")
        self.__class__.icon_press(self.replace, 1)
        self.replace.bind_property("secondary-icon-name", self.replace, "secondary-icon-tooltip-text", DEFAULT_BIND, self.__class__.icon_bind)
        self.replace.connect("activate", self.__class__.replace_activate)
        self.replace.connect("changed", self.__class__.replace_changed)
        self.replace.connect("icon-press", self.__class__.icon_press)
        b1, b2 = [Gtk.Box(hexpand=True, css_classes=["linked"]) for _ in range(2)]
        for i in (Button(icon_name="go-previous", tooltip_text="Previous", callback=self.__class__.go), self.find, Button(t=Gtk.MenuButton, icon_name="emblem-system", tooltip_text="Options", menu_model=Menu(dict((i, f"win.{i.lower().replace(' ', '-')}") for i in ("Regex", "Whole Words", "Case Sensitive")))), Button(icon_name="go-next", tooltip_text="Next", callback=self.__class__.go)): b1.append(i)
        for i in (self.replace,): b2.append(i)
        self.replace.bind_property("visible", b2, "visible", DEFAULT_BIND)
        for i in (b1, b2): box.append(i)
        self.bind_property("valign", self, "transition-type", DEFAULT_BIND, self.__class__.find_reveal_bind)

    def stop(self):
        self.find.set_text("")
        self.set_reveal_child(False)

    @staticmethod
    def find_activate(s):
        self = s.get_ancestor(Find)
        if self: self.move(True)

    @staticmethod
    def replace_activate(s):
        self = s.get_ancestor(Find)
        if self: self.do_replace()

    @staticmethod
    def icon_bind(b, v): return "All" if v and "-all" in v else "Selected"

    @staticmethod
    def icon_press(s, b):
        self = s.get_ancestor(Find)
        if self and b == 0: self.do_replace()
        if b == 1:
            v = s.get_property("secondary-icon-name")
            v = "" if v and "-all" in v else "-all"
            s.set_property("secondary-icon-name", "edit-select" + v + "-symbolic")

    @staticmethod
    def state_changed(a, s, self): self.__class__.changed(self.find)

    def do_replace(self):
        if self.changing or not self.find.get_text(): return
        window = self.get_root()
        view = window.view.get_selected_page().get_child().get_child()
        if view.context.get_regex_error(): return
        if view.context.get_settings().get_property("regex-enabled"):
            if not GLib.Regex.check_replacement(self.replace.get_text())[0]: return Toast("Invalid Replacement")
        if window.lookup_action("replace-all").get_state().unpack(): view.context.replace_all(self.replace.get_text(), -1)
        else:
            r = view.get_buffer().get_selection_bounds()
            if not r: return self.move(True, self.__class__.try_replace, (view, self.replace.get_text()))
            view.context.replace(r[0], r[1], self.replace.get_text(), -1)

    @staticmethod
    def try_replace(a):
        view, t = a
        r = view.get_buffer().get_selection_bounds()
        if r: view.context.replace(r[0], r[1], t, -1)

    def move(self, v=False, func=False, data=None):
        if self.changing: return
        window = self.get_root()
        tab = window.view.get_selected_page().get_child()
        if isinstance(tab.get_child(), Terminal) and tab.find:
            if v: tab.get_child().search_find_next()
            else: tab.get_child().search_find_previous()
        if isinstance(tab.get_child(), View) and tab.find and not tab.get_child().context.get_regex_error():
            i = tab.get_child().get_buffer().get_selection_bounds()
            if i and v:
                i = i[-1]
            elif i:
                i = i[0]
            s = tab.get_child().get_buffer().get_start_iter()
            i = i or s
            (tab.get_child().context.forward_async if v else tab.get_child().context.backward_async)(i, None, self.__class__.move_finish, ("forward" if v else "backward", tab.get_child(), func, data))

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
        if not self or self.changing: return
        self.move(b.get_tooltip_text() == "Next")

    @staticmethod
    def replace_changed(s):
        self = s.get_ancestor(Find)
        if not self or self.changing: return
        window = self.get_root()
        tab = window.view.get_selected_page().get_child()
        tab.replace = self.replace.get_text()

    @staticmethod
    def changed(s):
        self = s.get_ancestor(Find)
        if not self or self.changing: return
        window = self.get_root()
        if not window.view.get_selected_page(): return
        tab = window.view.get_selected_page().get_child()
        tab.find = self.find.get_text()
        if Vte and isinstance(tab.get_child(), Terminal):
            find = tab.find
            if not window.lookup_action("regex").get_state().unpack():
                find = GLib.Regex.escape_string(find, -1)
            flags = VTE_PCRE2_MULTILINE
            if not window.lookup_action("case-sensitive").get_state().unpack():
                flags = flags | VTE_PCRE2_CASELESS
            if window.lookup_action("whole-words").get_state().unpack():
                find = fr"\b{find}\b"
            if find:
                r = None
            else:
                r = Vte.Regex.new_for_search(find, -1, flags)
            tab.get_child().search_set_regex(r, 0)
            tab.get_child().search_set_wrap_around(True)
            self.move(True)
        if GtkSource and isinstance(tab.get_child(), View):
            tab.get_child().context.get_settings().set_property("regex-enabled", window.lookup_action("regex").get_state().unpack())
            tab.get_child().context.get_settings().set_property("case-sensitive", window.lookup_action("case-sensitive").get_state().unpack())
            tab.get_child().context.get_settings().set_property("at-word-boundaries", window.lookup_action("whole-words").get_state().unpack())
            find = tab.find
            if not tab.get_child().context.get_settings().get_property("regex-enabled"):
                find = GtkSource.utils_unescape_search_text(find)
            old = tab.get_child().context.get_settings().get_property("search-text")
            tab.get_child().context.get_settings().set_property("search-text", find)
            if tab.get_child().context.get_regex_error(): Toast("Invalid Search")
            elif old != find: self.move(True)

    @staticmethod
    def find_reveal_bind(b, v): return Gtk.RevealerTransitionType.SLIDE_DOWN if v == Gtk.Align.START else Gtk.RevealerTransitionType.SLIDE_UP

class Tab(Gtk.ScrolledWindow):
    __gtype_name__ = "Tab"
    context_menu = Menu({"Set Title": "win.tab-context-set-title"})

    tab = GObject.Property(type=Adw.TabPage)
    command = GObject.Property(type=str)
    find = GObject.Property(type=str)
    replace = GObject.Property(type=str)
    closed = []

    @classproperty
    def current(*_): return Window.current.view.get_selected_page().get_child() if Window.current and Window.current.view.get_selected_page() else None

    def __init__(self, command=False, view=None, title=False):
        super().__init__(css_name="tab")
        view = view or App.default.get_active_window().view
        current_tab = view.get_selected_page().get_child() if view.get_selected_page() else False
        self.tab = view.add_page(self, current_tab.tab if current_tab else None) if view.get_mapped() else view.append(self)
        self.command = command if isinstance(command, str) else App.default.PREFERENCES.new_tab_command
        self.set_title(title)

    def set_title(self, title):
        if title: self.tab.set_title(title)
        else: self.tab.set_title(basename(uri_decode(self.command)) if self.command.startswith("file://") else "Terminal" if self.command else "New File")

    @staticmethod
    def overview_create(*_): return Tab.create().tab

    @staticmethod
    def create(*_, view=False, command=False, title=False): return Tab(view=view if isinstance(view, Adw.TabView) else False, command=command, title=title)

    @staticmethod
    def new_file(*_): return Tab.create(command="")

    @staticmethod
    def setup_menu(v, t): v.get_root().set_property("context-tab", t)

    @staticmethod
    def action(a, p, window):
        tab = window.context_tab if "context" in a.get_name() else window.view.get_selected_page()
        if "set-title" in a.get_name():
            d = EntryPrompt(callback=Tab.do_change_title, heading="Set Tab Title")
            d.tab = tab
            d.present()

    @staticmethod
    def do_change_title(d):
        tab = d.tab
        del d.tab
        tab.set_title(d.get_extra_child().get_text())
        Tab.idle_save_all()

    @staticmethod
    def changed(view, *_):
        if not view.get_mapped(): return
        w = view.get_root()
        if not view.get_selected_page(): return
        tab = view.get_selected_page().get_child()
        if not tab.tab: return
        w.find.changing = True
        w.find.find.set_text(tab.find)
        w.find.replace.set_text(tab.replace)
        w.find.changing = False
        if tab.get_child():
            if hasattr(tab.get_child(), "changed"): tab.get_child().changed()
            w.find.replace.set_visible(GtkSource and isinstance(tab.get_child(), View))
        else:
            if GtkSource and (not tab.command or tab.command.startswith("file://")):
                View(tab.command, tab)
                w.find.replace.set_visible(True)
            elif Vte:
                tab.set_child(Terminal(tab.command))
                w.find.replace.set_visible(False)
        GLib.timeout_add(200, w.set_focus, tab.get_child())

    @staticmethod
    def idle_save_all(*_): Task.invoke(Tab.get_all, save=True)

    @staticmethod
    def get_all(save=False):
        tabs = []
        for w in App.default.get_windows():
            if not isinstance(w, Window) or save and not w.get_mapped(): continue
            for _id, i in enumerate(w.view.get_pages()):
                if save:
                    i.get_child().n = _id
                tabs.append(i.get_child())
        window_seen = []
        if save and Window.current and Window.current.get_mapped():
            for i in tabs:
                if i.get_root() and i.get_root().get_mapped():
                    if not i.get_root().get_id() in window_seen:
                        window_seen.append(i.get_root().get_id())
                        App.default.data.delete(table="Tabs", conditions="Window = ?", conds=(i.get_root().get_id(),))
                    App.default.data.new(table="Tabs", values=(i.get_root().get_id(), i.n + 1, i.command, i.tab.get_title()))
        return tabs

    @staticmethod
    def operation(a, b=False, t=False):
        view = a if isinstance(a, Adw.TabView) else App.default.get_active_window().view
        if not t:
            t = b if isinstance(b, Adw.TabPage) else view.get_root().context_tab if "context" in a.get_name() else view.get_selected_page()
            t = t.get_child()
        if not t: return
        view = t.get_ancestor(Adw.TabView)
        if isinstance(a, Adw.TabView) or isinstance(a, Gio.SimpleAction) and "close-tab" in a.get_name():
            if view: view.close_page(t.tab) if isinstance(a, Gio.SimpleAction) else None
            Tab.closed.append(t.command)
            App.default.lookup_action("reopen-tab").set_enabled(bool(Tab.closed))
            if hasattr(t, "pid") and t.pid > 10: GLib.spawn_command_line_async(f"kill -s 9 {t.pid}")

    @staticmethod
    def reopen(*_):
        if Tab.closed:
            p = Tab.closed.pop(-1)
            while p in Tab.closed: Tab.closed.remove(p)
            Tab.create(command=p)
            App.default.lookup_action("reopen-tab").set_enabled(bool(Tab.closed))

class Color(ListObject):
    __gtype_name__ = "Color"
    rgba = GObject.Property(type=RGBA)
    title = GObject.Property(type=str)

    @staticmethod
    def changed(self, p=None):
        a = [i.rgba.to_string() for i in App.default.PREFERENCES.colors]
        b = App.default.data.setting("Vte Palette", "#ffffff\n#1c1c1f\n#241f31\n#c01c28\n#2ec27e\n#f5c211\n#1e78e4\n#9841bb\n#0ab9dc\n#c0bfbc\n#5e5c64\n#ed333b\n#57e389\n#f8e45c\n#51a1ff\n#c061cb\n#4fd2fd\n#f6f5f4").split("\n")
        while len(a) > len(b): b.append("")
        for n, i in enumerate(a):
            b[n] = i
        App.default.data.setting("Vte Palette", None, "\n".join(b))
        for i in Terminal.get_all():
            i.colors = App.default.PREFERENCES.colors

class Preferences(Adw.PreferencesDialog):
    __gtype_name__ = "Preferences"
    new_tab_command = GObject.Property(type=str)
    cursor_shape = GObject.Property(type=str)
    show_line_numbers = GObject.Property(type=bool, default=True)
    highlight_current_line = GObject.Property(type=bool, default=True)
    vte_font = GObject.Property(type=Pango.FontDescription)
    colors = GObject.Property(type=List)
    style_scheme = (GObject.Property(type=GtkSource.StyleScheme) if GtkSource else None)
    source_font = GObject.Property(type=Pango.FontDescription)
    source_font_css =  GObject.Property(type=str)

    color_factory = Gtk.SignalListItemFactory.new()
    @staticmethod
    def setup(f, l): l.set_child(Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(), valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER))
    color_factory.connect("setup", setup)
    @staticmethod
    def bind(f, l):
        if not l.get_child(): return
        l.get_child().bindings = []
        Task.invoke(l.get_child().get_parent().set_properties, css_classes=[], focusable=False)
        l.get_child().bindings.append(l.get_property("item").bind_property("rgba", l.get_child(), "rgba", SYNC_BIND))
        l.get_child().bindings.append(l.get_property("item").bind_property("title", l.get_child(), "tooltip-text", DEFAULT_BIND))
    color_factory.connect("bind", bind)
    @staticmethod
    def unbind(f, l):
        for i in getattr(l.get_child(), "bindings", []): i.unbind()
        if hasattr(l.get_child(), "bindings"): del l.get_child().bindings
    color_factory.connect("unbind", unbind)
    @staticmethod
    def teardown(f, l): l.set_child(None)
    color_factory.connect("teardown", teardown)

    def __init__(self):
        super().__init__(content_width=600, content_height=600)
        App.default.PREFERENCES = self
        if GtkSource:
            GtkSource.LanguageManager.get_default().prepend_search_path(App.default.data_folder.peek_path())
            GtkSource.StyleSchemeManager.get_default().prepend_search_path(App.default.data_folder.peek_path())
            GtkSource.StyleSchemeManager.get_default().force_rescan()
        general = Adw.PreferencesPage(title="General", icon_name="applications-development-symbolic")
        theme = Adw.PreferencesPage(title="Theme", icon_name="applications-graphics-symbolic")
        for i in (general, theme): self.add(i)
        if Vte:
            group = Adw.PreferencesGroup(title="Vte")
            new_tab_command = Adw.EntryRow(title="New Tab Command", text=App.default.data.setting("New Tab Command", ""))
            new_tab_command.bind_property("text", self, "new-tab-command", DEFAULT_BIND)
            new_tab_command.connect("changed", self.__class__.setting_changed)
            cursor_shape = Adw.ActionRow(title="Cursor Shape")
            g = Adw.ToggleGroup(name="Vte Cursor Shape", valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
            cursor_shape.add_suffix(g)
            for i in ["Block", "Vertical Bar", "Horizontal Bar"]: g.add(Adw.Toggle(label=i, name=i))
            g.set_active_name(str(App.default.data.setting("Vte Cursor Shape", "Vertical Bar")))
            g.bind_property("active-name", self, "cursor-shape", SYNC_BIND)
            g.connect("notify::active", self.__class__.setting_changed)
            for i in (new_tab_command, cursor_shape): group.add(i)
            general.add(group)

        if GtkSource:
            group = Adw.PreferencesGroup(title="Source")
            for i in ("Show Line Numbers", "Highlight Current Line"):
                i = Adw.SwitchRow(title=i)
                i.set_active(App.default.data.setting(i.get_title(), getattr(self, i.get_title().lower().replace(" ", "_"))))
                self.bind_property(i.get_title().lower().replace(" ", "-"), i, "active", SYNC_BIND)
                i.connect("notify::active", self.__class__.setting_changed)
                group.add(i)
            general.add(group)

        if Vte:
            group = Adw.PreferencesGroup(title="Vte")
            font = FontRow(title="Font", font_desc=Pango.FontDescription.from_string(App.default.data.setting("Vte Font", "Adwaita Mono 20")), name="Vte Font")
            font.bind_property("font-desc", self, "vte-font", SYNC_BIND)
            font.connect("notify::font-desc", self.__class__.setting_changed)
            size = Adw.ExpanderRow(title="Palette Size")
            size.add_css_class("color")
            g = Adw.ToggleGroup(valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
            for i in ["0", "8", "16", "232", "256"]: g.add(Adw.Toggle(label=i, name=i))
            g.set_active_name(str(App.default.data.setting("Vte Palette Size", "16")))
            size.add_suffix(g)
            colors = Gtk.GridView(max_columns=10, min_columns=10, factory=self.__class__.color_factory, model=Gtk.NoSelection(), valign=Gtk.Align.START)
            colors.set_css_classes([])
            size.add_row(colors)
            self.bind_property("colors", colors.get_model(), "model", DEFAULT_BIND)
            g.bind_property("active-name", self, "colors", DEFAULT_BIND, self.__class__.palette_size_bind)
            for i in (font, size): group.add(i)
            theme.add(group)

        if GtkSource:
            group = Adw.PreferencesGroup(title="Source")
            b = GtkSource.StyleSchemeChooserButton(name="Source Style Scheme", valign=Gtk.Align.CENTER)
            b.bind_property("style-scheme", self, "style-scheme", SYNC_BIND)
            v = App.default.data.setting("Source Style Scheme", "Adwaita-dark")
            if v in GtkSource.StyleSchemeManager.get_default().get_scheme_ids(): b.set_style_scheme(GtkSource.StyleSchemeManager.get_default().get_scheme(v))
            b.connect("notify::style-scheme", self.__class__.setting_changed)
            font = FontRow(title="Font", font_desc=Pango.FontDescription.from_string(App.default.data.setting("Source Font", "Adwaita Mono 20")), name="Source Font")
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
        default_colors = App.default.data.setting("Vte Palette", "#ffffff\n#1c1c1f\n#241f31\n#c01c28\n#2ec27e\n#f5c211\n#1e78e4\n#9841bb\n#0ab9dc\n#c0bfbc\n#5e5c64\n#ed333b\n#57e389\n#f8e45c\n#51a1ff\n#c061cb\n#4fd2fd\n#f6f5f4").split("\n")
        l.append(Color(title="Foreground", rgba=RGBA(default_colors[0])))
        l.append(Color(title="Background", rgba=RGBA(default_colors[1])))
        default_colors = default_colors[2:]
        for n in range(int(v) if v.isdigit() else 0): l.append(Color(rgba=RGBA(default_colors[n] if len(default_colors) > n else ""), title=str(n + 1)))
        App.default.data.setting("Vte Palette Size", None, v)
        return l

    @staticmethod
    def setting_changed(w, p=None):
        if isinstance(w, Adw.ToggleGroup): App.default.data.setting(w.get_name(), None, w.get_active_name())
        if isinstance(w, Adw.EntryRow): App.default.data.setting(w.get_title(), None, w.get_text())
        if isinstance(w, FontRow):
            font = w.get_font_desc()
            App.default.data.setting(w.get_name(), None, font.to_string())
            if w.get_name() == "Source Font":
                App.default.PREFERENCES.source_font_css = "textview { font-family: " + font.get_family() + "; font-size: " + str(int(font.get_size() / Pango.SCALE)) + "pt; }"
        if isinstance(w, GtkSource.StyleSchemeChooserButton): App.default.data.setting(w.get_name(), None, w.get_style_scheme().get_id())

    @staticmethod
    def show(*_):
        if App.default.PREFERENCES.get_mapped(): Preferences.close()
        App.default.PREFERENCES.present()

if GtkSource:
    class View(GtkSource.View):
        __gtype_name__ = "View"
        file = GObject.Property(type=GtkSource.File)
        cancel = GObject.Property(type=Gio.Cancellable)
        tab = GObject.Property(type=Tab)
        context = GObject.Property(type=GtkSource.SearchContext)
        def __init__(self, uri, tab, **kwargs):
            super().__init__(right_margin=0, left_margin=0, wrap_mode=Gtk.WrapMode.WORD_CHAR, auto_indent=True, indent_width=4, insert_spaces_instead_of_tabs=True, tab_width=4, smart_backspace=True, smart_home_end=GtkSource.SmartHomeEndType.ALWAYS)
            self.context = GtkSource.SearchContext.new(self.get_buffer())
            self.context.get_settings().set_property("wrap-around", True)
            self.tab = tab
            self.get_buffer().set_max_undo_levels(0)
            self.get_buffer().bind_property("loading", tab.tab, "loading", DEFAULT_BIND)
            self.get_buffer().set_implicit_trailing_newline(False)
            App.default.PREFERENCES.bind_property("style-scheme", self.get_buffer(), "style-scheme", DEFAULT_BIND)
            self.file = GtkSource.File.new()
            self.file.set_location(Gio.File.new_for_uri(uri) if uri else None)
            self.__class__.reload_file(self)
            self.set_css_classes([])
            self.connect("notify::show-line-numbers", self.__class__.change_margin)
            App.default.PREFERENCES.bind_property("show-line-numbers", self, "show-line-numbers", DEFAULT_BIND)
            App.default.PREFERENCES.bind_property("highlight-current-line", self, "highlight-current-line", DEFAULT_BIND)

        def changed(self):
            self.file.check_file_on_disk()
            if self.file.is_externally_modified():
                d = Prompt(heading="Reload File?", body="File has changed on disk", callback=self.__class__.reload_file)
                d.view = self
                d.present(self.get_root())

        @staticmethod
        def reload_file(d):
            self = d if isinstance(d, View) else d.view
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
                a.load_finish(r)
            if self.tab: self.tab.set_child(self)
            self.tab = None

        @staticmethod
        def change_margin(self, p=None): self.set_left_margin(10 if self.get_property("show-line-numbers") else 0)

        def save(self): GtkSource.FileSaver.new(self.get_buffer(), self.file).save_async(GLib.PRIORITY_DEFAULT, self.cancel, None, None, self.__class__.do_save_finish, self)

        @staticmethod
        def do_save_dialog(a, r, self):
            try:
                f = a.save_finish(r)
            except: return
            self.file.set_location(f)
            tab = self.get_ancestor(Tab)
            tab.command = f.get_uri()
            tab.set_title(False)
            self.save()
            Tab.idle_save_all()

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
                else:
                    Toast(f"{e} {l.get_uri()}", timeout=0)

        @staticmethod
        def overwrite_file(d):
            self = d.view
            del d.view
            l = self.file.get_location()
            self.file = GtkSource.File.new()
            self.file.set_location(l)
            self.save()
else:
    View = False

if Vte:
    class Terminal(Vte.Terminal):
        __gtype_name__ = "Terminal"

        @GObject.Property(type=List)
        def colors(self): return getattr(self, "_colors", None)

        @colors.setter
        def colors(self, value):
            setattr(self, "_colors", value)
            l = [i.rgba.copy() if i.rgba else Gdk.RGBA() for i in self.colors]
            self.set_colors(l[0], l[1], l[2:])

        def __init__(self, command):
            super().__init__(scrollback_lines=1024, allow_hyperlink=True, enable_sixel=True)
            self.colors = App.default.PREFERENCES.colors
            App.default.PREFERENCES.bind_property("vte-font", self, "font-desc", SYNC_BIND)
            App.default.PREFERENCES.bind_property("cursor-shape", self, "cursor-shape", SYNC_BIND, self.__class__.shape_bind)
            self.connect("child-exited", self.__class__.child_exited)
            self.spawn_async(Vte.PtyFlags.DEFAULT, None, GLib.shell_parse_argv(command)[-1], None, GLib.SpawnFlags.DEFAULT, None, None, GLib.MAXINT, None, self.__class__.finish_spawn, None)

        @staticmethod
        def shape_bind(b, v): return Vte.CursorShape.IBEAM if v == "Vertical Bar" else Vte.CursorShape.UNDERLINE if v == "Horizontal Bar" else 0

        @staticmethod
        def finish_spawn(v, p, e=None, d=None):
            self = v.get_parent()
            self.pid = p

        @staticmethod
        def child_exited(v, s):
            self = v.get_parent()
            if hasattr(self, "pid"):
                del self.pid
                Tab.operation(App.default.lookup_action("close-tab"), b=None, t=self)

        @staticmethod
        def get_all():
            l = []
            for i in Tab.get_all():
                if isinstance(i.get_child(), Terminal): l.append(i.get_child())
            return l
else:
    Terminal = False

def handle_command(a, ar):
    ar = ar.get_arguments()
    if len(ar) >= 1:
        ar = ar[1:]
    if App.default.get_active_window(): App.default.get_active_window().present()
    else:
        d = a.data.read(table="Windows", column="ID", force_tuple=True)
        if not d:
            a.data.set_default(table="Windows", conditions="ID = '1'", values=(1,), names=("ID",))
            d = [1]
        for i in d: Window(i)
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
main-header { padding: 0px 5px; }
main-header > menubutton { margin-left: 5px; }
tabbar > revealer > box { padding: 0px; }
widget > tab > textview,
widget > tab > textview border,
widget > tab > textview border gutter,
widget > tab > textview text { background: none; }
widget > tab > vte-terminal { padding: 6px; }
.fullscreen find { margin-top: 6px; }
find > search { border-spacing: 6px; }
find > search > box { border-radius: 9px; backdrop-filter: blur(20px) brightness(0.9); background: color-mix(in srgb, var(--window-bg-color) 35%, transparent); }
row.color gridview { border-spacing: 0px 12px; padding: 6px 0px; }
row.color gridview child { padding: 0px; }
"""

DATA_INIT = """
CREATE TABLE IF NOT EXISTS Tabs (Window INTEGER NOT NULL DEFAULT 1, ID INTEGER, Command TEXT DEFAULT '', Title TEXT DEFAULT '', UNIQUE ('Window', 'ID'), FOREIGN KEY (Window) REFERENCES Windows(ID) ON DELETE CASCADE ON UPDATE CASCADE);
CREATE TABLE IF NOT EXISTS Windows (ID INTEGER PRIMARY KEY AUTOINCREMENT, 'Default Width' INTEGER NOT NULL DEFAULT 360, 'Default Height' INTEGER NOT NULL DEFAULT 760, 'Fullscreen' INTEGER NOT NULL DEFAULT 0, Maximized INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS Settings (Key TEXT PRIMARY KEY NOT NULL, Value TEXT);
"""

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
    App.default.get_style_manager().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
    if GtkSource: App.default.set_accels_for_action("win.open-files", ["<primary>o"])
    Preferences()
    App.default.main(css=APP_CSS)

if __name__ == "__main__": main()