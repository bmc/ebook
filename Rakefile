# coding: utf-8
#                                                             -*- ruby -*-
# Generate the book output, in EPUB, PDF and HTML forms.
#
# To build, you need:
#
# 1. Pandoc (http://johnmacfarlane.net/pandoc), version 1.6 or better. On a
#    Mac, "brew install pandoc".
#
# 2. A TexLive distribution, to generate the PDF.
#    a) Use MacTex on the Mac (http://www.tug.org/mactex/)
#       - Put /usr/local/texlive/2010/bin/universal-darwin in the path
#    b) On Ubuntu/Debian, install:
#       - texlive
#       - texlive-latex-recommended
#       - texlive-latex-extras
#
# 3. A Python 3 distribution, with the "panflute" package installed
#    ("pip install panflute").
#
# 4. Ruby and Rake, to run this file.
# ---------------------------------------------------------------------------

require 'rubygems'
require 'open3'
require './book-metadata.rb'

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Generated files
PREFIX       = 'book'
OUTPUT_HTML  = "#{PREFIX}.html"
OUTPUT_PDF   = "#{PREFIX}.pdf"
OUTPUT_EPUB  = "#{PREFIX}.epub"
OUTPUT_DOCX  = "#{PREFIX}.docx"
OUTPUT_LATEX = "#{PREFIX}.latex"
OUTPUT_JSON  = "#{PREFIX}.json"
TITLE_TXT    = "#{PREFIX}-title.txt"
LATEX_TITLE  = 'latex-title.latex'

# Input files
def maybe_file(f)
  File.exists?(f) ? [f] : []
end

CHAPTERS           = FileList['chapter-*.md'].sort
COPYRIGHT_TEMPLATE = 'copyright-template.md'
COPYRIGHT          = '_copyright.md'
INPUT_FILE_LIST    = [COPYRIGHT] +
                     maybe_file("dedication.md") +
                     maybe_file("prologue.md") +
                     CHAPTERS +
                     maybe_file("epilogue.md") +
                     maybe_file("acknowledgments.md")
INPUT_FILES        = INPUT_FILE_LIST.join(' ')
HTML_CSS           = 'html.css'
EPUB_CSS           = 'epub.css'
EPUB_METADATA      = 'epub-metadata.xml'
LATEX_HEADER       = 'latex-header.txt'
LATEX_TEMPLATE     = 'latex.template'
PANDOC_FILTER      = "./pandoc-filter.py"

# Lists of dependencies, for ease of reference.
DEPS       = INPUT_FILE_LIST + FileList['Rakefile'] + FileList[PANDOC_FILTER]
EPUB_DEPS  = DEPS + FileList[COVER_IMAGE, EPUB_METADATA, EPUB_CSS, TITLE_TXT]
HTML_DEPS  = DEPS + FileList[HTML_CSS, TITLE_TXT]
PDF_DEPS   = DEPS + FileList[LATEX_HEADER, LATEX_TITLE]
LATEX_DEPS = DEPS + FileList[LATEX_HEADER, LATEX_TITLE, LATEX_TEMPLATE]
DOCX_DEPS  = DEPS

# +RTS and -RTS delimit Haskell runtime options. See
# http://www.haskell.org/ghc/docs/6.12.2/html/users_guide/runtime-control.html
#
# -Ksize sets the stack size. -K10m uses a 10 Mb stack, for instance. The
# default size is 8M.

HASKELL_OPTS = '+RTS -K20m -RTS '
#HASKELL_OPTS = ''
INPUT_FORMAT = "markdown+line_blocks+escaped_line_breaks"
COMMON_PANDOC_OPTS = "-F #{PANDOC_FILTER} -s -f #{INPUT_FORMAT} --smart #{HASKELL_OPTS} "
NON_LATEX_PANDOC_OPTS = COMMON_PANDOC_OPTS + "--top-level-division=chapter"
LATEX_PANDOC_OPTS = "#{COMMON_PANDOC_OPTS} --template=latex.template"

# ---------------------------------------------------------------------------
#
# ---------------------------------------------------------------------------

task :default => [:all]

task :all => [:html, :pdf, :epub, :docx]
task :remake => [:clean, :all]
task :html => OUTPUT_HTML
task :pdf => OUTPUT_PDF
task :epub => OUTPUT_EPUB
task :docx => OUTPUT_DOCX
task :title => TITLE_TXT
task :latex => OUTPUT_LATEX

task :clean do
  Dir.glob('*.bak').each { |f| rm_f f }
  [OUTPUT_HTML, OUTPUT_EPUB, OUTPUT_PDF, OUTPUT_DOCX, OUTPUT_LATEX,
   TITLE_TXT, LATEX_TITLE, OUTPUT_JSON, COPYRIGHT].each do |f|
    rm_f f
  end
end

desc "Generate Pandoc JSON, for debugging."
task 'json' => OUTPUT_JSON

desc "Generate Pandoc JSON, for debugging."
task "book.json" => HTML_DEPS do |t|
  preprocess_markdown *INPUT_FILE_LIST do |path|
    sh "pandoc #{NON_LATEX_PANDOC_OPTS} -o #{t.name} -t json -css=#{HTML_CSS} #{TITLE_TXT} #{path}"
  end
end

file OUTPUT_HTML => HTML_DEPS do |t|
  preprocess_markdown *INPUT_FILE_LIST do |path|
    sh "pandoc #{NON_LATEX_PANDOC_OPTS} -o #{t.name} -t html -css=#{HTML_CSS} #{TITLE_TXT} #{path}"
  end
end

file OUTPUT_PDF => LATEX_DEPS do |t|
  preprocess_markdown *INPUT_FILE_LIST do |path|
    sh "pandoc #{LATEX_PANDOC_OPTS} -o #{t.name} #{LATEX_HEADER} #{LATEX_TITLE} #{path}"
  end
end

file OUTPUT_LATEX => LATEX_DEPS do |t|
  preprocess_markdown *INPUT_FILE_LIST do |path|
    sh "pandoc #{LATEX_PANDOC_OPTS} -o #{t.name} #{LATEX_HEADER} #{LATEX_TITLE} #{path}"
  end
end

file OUTPUT_DOCX => DOCX_DEPS do |t|
  preprocess_markdown *INPUT_FILE_LIST do |path|
    sh "pandoc #{NON_LATEX_PANDOC_OPTS} -o #{t.name} -t docx #{TITLE_TXT} #{path}"
  end
end

file OUTPUT_EPUB => EPUB_DEPS do |t|
  preprocess_markdown *INPUT_FILE_LIST do |path|
    sh("pandoc #{NON_LATEX_PANDOC_OPTS} -o #{t.name} -t epub --toc " +
       "--epub-stylesheet=#{EPUB_CSS} --epub-metadata=#{EPUB_METADATA} " +
       "--epub-cover-image=#{COVER_IMAGE} #{TITLE_TXT} #{path}")
  end
end

file COPYRIGHT => ['Rakefile', COPYRIGHT_TEMPLATE] do
  puts "#{COPYRIGHT_TEMPLATE} -> #{COPYRIGHT}"
  File.open(COPYRIGHT, 'w') do |out|
    File.open(COPYRIGHT_TEMPLATE, 'r').each do |line|
      line.gsub!("@YEAR@", COPYRIGHT_YEAR.to_s)
      line.gsub!("@OWNER@", COPYRIGHT_OWNER)
      out.write(line)
    end
  end
end

file EPUB_METADATA => ['Rakefile'] do
  File.open(EPUB_METADATA, 'w') do |f|
    f.write <<EOT
<dc:rights>Copyright &#xa9; 2017 #{COPYRIGHT_OWNER}</dc:rights>
<dc:language>en-US</dc:language>
<dc:publisher>#{PUBLISHER}</dc:publisher>
<dc:subject>Fantasy</dc:subject>
EOT
  end
end

file TITLE_TXT => 'Rakefile' do |t|
  File.open(TITLE_TXT, 'w') do |f|
    f.print <<EOT
% #{TITLE}
% #{AUTHOR}

EOT
  end
end

# Note: The following requires a custom LaTeX template with
# \usepackage{graphicx} in the preamble.
file LATEX_TITLE => 'Rakefile' do |t|
  File.open(LATEX_TITLE, 'w') do |f|
    f.print <<EOT
\\begin{titlepage}
\\includegraphics{cover.png}
\\end{titlepage}
EOT
  end
end

file LATEX_TEMPLATE do |t|
  Open3.popen2e('pandoc -D latex') do |_, pipe_out, _|
    File.open(LATEX_TEMPLATE, 'w') do |t|
      pipe_out.each_with_index do |line, i|
        # Emit our custom \usepackage after line 1.
        t.puts("\\usepackage{graphicx}") if i == 1
        t.puts(line)
      end
    end
  end
end

task :x do
  preprocess_markdown *INPUT_FILE_LIST do |temp_path|
    sh "pandoc #{LATEX_PANDOC_OPTS} -o book.pdf #{LATEX_HEADER} #{LATEX_TITLE} #{temp_path}"
  end
end

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def preprocess_markdown(*inputs)
  puts "Preprocessing: #{inputs}"
  File.open('_temp.md', 'w') do |t|
    inputs.each do |f|
      File.open(f).each do |line|
        t.puts(line.chomp)
      end
      # Force a newline after each file section.
      t.puts("\n")
    end
  end
  begin
    yield '_temp.md'
  ensure
    File.unlink('_temp.md')
  end
end

