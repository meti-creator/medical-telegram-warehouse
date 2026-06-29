{% macro generate_schema_name(custom_schema_name, node) -%}

    {#
        Override dbt's default behavior, which concatenates the target
        schema (from profiles.yml) with the custom schema (from dbt_project.yml),
        producing things like "staging_marts". We want the custom schema
        name used directly instead - so "marts" stays "marts", not "staging_marts".
    #}

    {%- if custom_schema_name is not none -%}

        {{ custom_schema_name | trim }}

    {%- else -%}

        {{ target.schema }}

    {%- endif -%}

{%- endmacro %}
