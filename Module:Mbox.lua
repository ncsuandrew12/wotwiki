-- This Module is used for making templates based in the Lua language.
-- See more details about Lua in [[Help:Lua]].
-- The Fandom Developer's Wiki hosts Global Lua Modules that can be imported and locally overridden.
-- The next line imports the Mbox module from the [[w:c:dev:Global Lua Modules]].
local Mbox = require('Dev:Mbox')
-- See more details about this module at [[w:c:dev:Global_Lua_Modules/Mbox]]

-- The imported Module is overwritten locally to include default styling.
-- For a more flexible Mbox experience, delete the function below and import 
-- https://dev.fandom.com/wiki/MediaWiki:Global_Lua_Modules/Mbox.css
-- or paste (and modify as you like) its contents in your wiki's 
-- [[MediaWiki:Wikia.css]] (see [[Help:Including_additional_CSS_and_JS]])
-- or look at https://dev.fandom.com/wiki/Global_Lua_Modules/Mbox
-- for more customization inspiration

-- 
-- BEGIN DELETION HERE
--

local getArgs = require('Dev:Arguments').getArgs
local localCSS = mw.loadData('Module:Mbox/data').localStyle

function Mbox.main(frame)
    local args = getArgs(frame)

    -- styles
    local styles = {}
    if args.bordercolor then
        styles['border-left-color'] = args.bordercolor
    elseif args.type then
        styles['border-left-color'] = 'var(--type-' .. args.type .. ')'
    end

    if args.bgcolor then
        styles['background-color'] = args.bgcolor
    end

    -- images
    local image = args.image or ''
    local imagewidth = args.imagewidth or '80px'
    local imagelink = ''
    if args.imagelink then
        imagelink = '|link=' .. args.imagelink
    end

    local imagewikitext = '[['..'File:' .. image .. '|' .. imagewidth .. imagelink .. ']]'

    -- id for closure
    local id = args.id or 'mbox'

    local container = mw.html.create('div')
        :addClass('mbox')
        :addClass(args.class)
        :css(styles)
        :css(localCSS['mbox'])
        :cssText(args.style)

    local content = container:tag('div')
        :addClass('mbox__content')
        :css(localCSS['mbox__content'])

    if args.image then
        local image = content:tag('div')
            :addClass('mbox__content__image')
            :addClass('mw-collapsible')
            :attr('id', 'mw-customcollapsible-' .. id)
        :css(localCSS['mbox__content__image'])
            :wikitext(imagewikitext)
            if args.collapsed then
                image:addClass('mw-collapsed')
            end
    end

    local contentwrapper = content:tag('div')
        :addClass('mbox__content__wrapper')
        :css(localCSS['mbox__content__wrapper'])

    if args.header then
        contentwrapper:tag('div')
            :addClass('mbox__content__header')
            :css(localCSS['mbox__content__header'])
            :wikitext(args.header)
    end

    if args.text then
        local text = contentwrapper:tag('div')
            :addClass('mbox__content__text')
            :addClass('mw-collapsible')
            :attr('id', 'mw-customcollapsible-' .. id)
            :css(localCSS['mbox__content__text'])
            :wikitext(args.text)
            if args.collapsed then
                text:addClass('mw-collapsed')
            end

        if args.comment then
            text:tag('div')
                :addClass('mbox__content__text__comment')
                :css(localCSS['mbox__content__text__comment'])
                :wikitext(args.comment)
        end
    end

    contentwrapper:tag('span')
        :addClass('mbox__close')
        :addClass('mw-customtoggle-' .. id)
        :css(localCSS['mbox__close'])
        :attr('title', 'Dismiss')

    if args.aside then
        local aside = content:tag('div')
            :addClass('mbox__content__aside')
            :addClass('mw-collapsible')
            :attr('id', 'mw-customcollapsible-' .. id)
            :css(localCSS['mbox__content__aside'])
            :wikitext(args.aside)
            if args.collapsed then
                aside:addClass('mw-collapsed')
            end
    end

    return container
end

-- 
-- END DELETION HERE
--

-- The last line produces the output for the template
return Mbox