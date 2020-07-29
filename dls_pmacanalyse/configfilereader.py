import configparser

from click_configfile import (
    ConfigFileReader,
    generate_configfile_names,
    select_config_sections,
)


# subclass ConfigFileReader so that you can pass any parameters to
# the underlying ConfigParser
# Unfortunately this involves cut and paste of read_config function
# a PR will resolve this https://github.com/click-contrib/click-configfile/pull/7
class ConfigFileReader2(ConfigFileReader):
    @classmethod
    def read_config(cls, **args):
        configfile_names = list(
            generate_configfile_names(cls.config_files, cls.config_searchpath)
        )
        parser = configparser.ConfigParser(**args)
        parser.optionxform = str
        parser.read(configfile_names)

        if not cls.config_sections:
            # -- AUTO-DISCOVER (once): From cls.config_section_schemas
            cls.config_sections = cls.collect_config_sections_from_schemas()

        storage = {}
        for section_name in select_config_sections(
            parser.sections(), cls.config_sections
        ):
            # print("PROCESS-SECTION: %s" % section_name)
            config_section = parser[section_name]
            cls.process_config_section(config_section, storage)
        return storage
