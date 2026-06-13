from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, "")


@register.filter
def filesizeformat(value):
    if not value:
        return "0 B"
    from django.template.defaultfilters import filesizeformat as django_fs
    return django_fs(value)
