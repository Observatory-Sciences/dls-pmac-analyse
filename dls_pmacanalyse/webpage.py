import xml.dom.minidom as minidom


class WebPage(object):
    def __init__(self, title, fileName, styleSheet=None):
        """Initialises a web page, creating all the necessary header stuff"""
        self.fileName = fileName
        self.doc = minidom.getDOMImplementation().createDocument(None, "html", None)
        self.topElement = self.doc.documentElement
        h = self.doc.createElement("head")
        self.topElement.appendChild(h)
        if styleSheet is not None:
            link = self.doc.createElement("link")
            h.appendChild(link)
            link.setAttribute("rel", "stylesheet")
            link.setAttribute("type", "text/css")
            link.setAttribute("href", styleSheet)
        t = self.doc.createElement("title")
        self.topElement.appendChild(t)
        t.appendChild(self.doc.createTextNode(str(title)))
        self.theBody = self.doc.createElement("body")
        self.topElement.appendChild(self.theBody)
        h = self.doc.createElement("h1")
        self.theBody.appendChild(h)
        h.appendChild(self.doc.createTextNode(str(title)))

    def body(self):
        return self.theBody

    def href(self, parent, tag, descr):
        """Creates a hot link."""
        a = self.doc.createElement("a")
        parent.appendChild(a)
        a.setAttribute("href", tag)
        a.appendChild(self.doc.createTextNode(descr))

    def lineBreak(self, parent):
        """Creates a line break."""
        parent.appendChild(self.doc.createElement("br"))

    def doc_node(self, text, desc):
        anode = self.doc.createElement("a")
        anode.setAttribute("class", "body_con")
        anode.setAttribute("title", desc)
        self.text(anode, text)
        return anode

    def text(self, parent, t):
        """Creates text."""
        parent.appendChild(self.doc.createTextNode(str(t)))

    def paragraph(self, parent, text=None, id=None):
        """Creates a paragraph optionally containing text"""
        para = self.doc.createElement("p")
        if id is not None:
            para.setAttribute("id", id)
        if text is not None:
            para.appendChild(self.doc.createTextNode(str(text)))
        parent.appendChild(para)
        return para

    def write(self):
        """Writes out the HTML file."""
        wFile = open(self.fileName, "w+")
        self.doc.writexml(wFile, indent="", addindent="", newl="")

    def table(self, parent, colHeadings=None, id=None):
        """Returns a table with optional column headings."""
        table = self.doc.createElement("table")
        if id is not None:
            table.setAttribute("id", id)
        parent.appendChild(table)
        if colHeadings is not None:
            row = self.doc.createElement("tr")
            if id is not None:
                row.setAttribute("id", id)
            table.appendChild(row)
            for colHeading in colHeadings:
                col = self.doc.createElement("th")
                if id is not None:
                    col.setAttribute("id", id)
                row.appendChild(col)
                col.appendChild(self.doc.createTextNode(str(colHeading)))
        return table

    def tableRow(self, table, columns=None, id=None):
        """Returns a table row, optionally with columns already created."""
        row = self.doc.createElement("tr")
        if id is not None:
            row.setAttribute("id", id)
        table.appendChild(row)
        if columns is not None:
            for column in columns:
                col = self.doc.createElement("td")
                if id is not None:
                    col.setAttribute("id", id)
                row.appendChild(col)
                col.appendChild(self.doc.createTextNode(str(column)))
        return row

    def tableColumn(self, tableRow, text=None, id=None):
        """Returns a table column, optionally containing the text."""
        col = self.doc.createElement("td")
        if id is not None:
            col.setAttribute("id", id)
        tableRow.appendChild(col)
        if text is not None:
            if hasattr(text, "appendChild"):
                # this is a node
                col.appendChild(text)
            else:
                col.appendChild(self.doc.createTextNode(str(text)))
        return col

    def emphasize(self, parent, text=None):
        """Returns an emphasis object, optionally containing the text."""
        result = self.doc.createElement("em")
        parent.appendChild(result)
        if text is not None:
            result.appendChild(self.doc.createTextNode(str(text)))
        return result
