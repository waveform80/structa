<?xml version="1.0"?>
<transform version="1.0" xmlns="http://www.w3.org/1999/XSL/Transform">

<output output="text" omit-xml-declaration="yes" />
<strip-space elements="*" />

<param name="normal-style" select="''" />
<param name="unique-style" select="'*'" />
<param name="key-style" select="$normal-style" />
<param name="type-style" select="$normal-style" />
<param name="stats-style" select="$normal-style" />
<param name="pattern-style" select="$stats-style" />
<param name="literal-style" select="$stats-style" />
<param name="req-style" select="''" />
<param name="opt-style" select="'?'" />
<param name="ellipsis" select="'..'" />
<param name="truncation" select="$ellipsis" />

<param name="show-pattern" select="1" />
<param name="show-lengths" select="0" />
<param name="show-range" select="1" />

<template name="sep">
    <value-of select="$normal-style" />
    <if test="not(position()=last())">, </if>
</template>

<template name="unique">
    <if test="values/summary[@unique]">
        <value-of select="$unique-style" />
    </if>
</template>

<variable name="spaces" select="'                                                                               '" />
<template name="indent">
    <param name="level" select="count(ancestor::dict|ancestor::list|ancestor::tuple)" />
    <text>&#xA;</text><value-of select="substring($spaces, 1, $level * 4)" />
</template>

<template match="dict[content//dict|content//list|content//tuple]|dict[count(content/*) &gt; 1]">
    <value-of select="$normal-style" />
    <text>{</text>
    <for-each select="content/*">
        <call-template name="indent" />
        <apply-templates select="." />
        <call-template name="sep" />
    </for-each>
    <call-template name="indent" />
    <value-of select="$normal-style" />
    <text>}</text>
</template>

<template match="list[content//dict|content//list|content//tuple]|list[count(content/*) &gt; 1]">
    <value-of select="$normal-style" />
    <text>[</text>
    <for-each select="content/*">
        <call-template name="indent" />
        <apply-templates select="." />
        <call-template name="sep" />
    </for-each>
    <call-template name="indent" />
    <value-of select="$normal-style" />
    <text>]</text>
</template>

<template match="tuple[content//dict|content//list|content//tuple]|tuple[count(content/*) &gt; 1]">
    <value-of select="$normal-style" />
    <text>(</text>
    <for-each select="content/*">
        <call-template name="indent" />
        <apply-templates select="." />
        <call-template name="sep" />
    </for-each>
    <call-template name="indent" />
    <value-of select="$normal-style" />
    <text>)</text>
</template>

<template match="dict">
    <text>{ </text>
    <for-each select="content/*">
        <apply-templates select="." />
        <call-template name="sep" />
    </for-each>
    <text> }</text>
</template>

<template match="list">
    <text>[ </text>
    <for-each select="content/*">
        <apply-templates select="." />
        <call-template name="sep" />
    </for-each>
    <text> ]</text>
</template>

<template match="tuple">
    <text>( </text>
    <for-each select="content/*">
        <apply-templates select="." />
        <call-template name="sep" />
    </for-each>
    <text> )</text>
</template>

<template match="field">
    <choose>
        <when test="*[position()=1 and @optional]"><value-of select="$opt-style" /></when>
        <otherwise><value-of select="$req-style" /></otherwise>
    </choose>
    <apply-templates select="*[1]" />
    <value-of select="$normal-style" />
    <text>: </text>
    <apply-templates select="*[2]" />
</template>

<template match="key">
    <value-of select="$key-style" />
    <value-of select="." />
</template>

<template match="str">
    <call-template name="unique" />
    <value-of select="$type-style" />
    <text>str</text>
    <if test="$show-pattern and pattern">
        <value-of select="$stats-style" />
        <text> pattern="</text>
        <apply-templates select="pattern" />
        <value-of select="$stats-style" />
        <text>"</text>
    </if>
    <apply-templates select="lengths" />
</template>

<template match="url">
    <call-template name="unique" />
    <value-of select="$type-style" />
    <text>URL</text>
</template>

<template match="float">
    <call-template name="unique" />
    <value-of select="$type-style" />
    <text>float</text>
    <apply-templates select="values" />
</template>

<template match="int">
    <call-template name="unique" />
    <value-of select="$type-style" />
    <text>int</text>
    <apply-templates select="values" />
</template>

<template match="bool">
    <call-template name="unique" />
    <value-of select="$type-style" />
    <text>bool</text>
</template>

<template match="datetime">
    <call-template name="unique" />
    <value-of select="$type-style" />
    <text>timestamp</text>
    <apply-templates select="values" />
</template>

<template match="value">
    <value-of select="$type-style" />
    <text>value</text>
</template>

<template match="empty">
    <value-of select="$type-style" />
    <text>empty</text>
</template>

<template match="strof">
    <value-of select="$type-style" />
    <text>str of </text><apply-templates select="*[not(self::pattern)]" />
    <if test="$show-pattern and pattern">
        <value-of select="$stats-style" />
        <text> pattern=</text>
        <apply-templates select="pattern" />
    </if>
</template>

<template match="intof">
    <value-of select="$type-style" />
    <text>int of </text><apply-templates select="*[not(self::pattern)]" />
</template>

<template match="floatof">
    <value-of select="$type-style" />
    <text>float of </text><apply-templates />
</template>

<template match="values">
    <if test="$show-range">
        <value-of select="$stats-style" />
        <text> range=</text>
        <apply-templates select="summary" />
    </if>
</template>

<template match="lengths">
    <if test="$show-lengths">
        <value-of select="$stats-style" />
        <text> lengths=</text>
        <apply-templates select="summary" />
    </if>
</template>

<template match="summary">
    <value-of select="min" />
    <choose>
        <when test="$show-range = 4">
            <text> [</text>
            <apply-templates select="graph" />
            <text>] </text>
        </when>
        <otherwise>
            <if test="$show-range &gt; 2">
                <value-of select="$ellipsis" />
                <value-of select="q1" />
            </if>
            <if test="$show-range &gt; 1">
                <value-of select="$ellipsis" />
                <value-of select="q2" />
            </if>
            <if test="$show-range &gt; 2">
                <value-of select="$ellipsis" />
                <value-of select="q3" />
            </if>
            <value-of select="$ellipsis" />
        </otherwise>
    </choose>
    <value-of select="max" />
</template>

<template match="pat">
    <value-of select="$pattern-style" />
    <apply-templates />
</template>

<template match="lit">
    <value-of select="$literal-style" />
    <apply-templates />
</template>

</transform>
