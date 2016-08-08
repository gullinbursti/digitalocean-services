from kik.messages.keyboards import SuggestedResponseKeyboard, UnknownKeyboard
from kik.messages.message import Message


keyboard_type_mapping = {
    'suggested': SuggestedResponseKeyboard
}


class KeyboardMessage(Message):
    """
    Parent class for messages that support keyboards.
    """
    def __init__(self, keyboards=None, **kwargs):
        super(KeyboardMessage, self).__init__(**kwargs)
        if keyboards:
            self.keyboards = keyboards
        else:
            self.keyboards = []

    def to_json(self):
        output_json = super(KeyboardMessage, self).to_json()
        if len(self.keyboards) > 0:
            output_json['keyboards'] = [keyboard.to_json() for keyboard in self.keyboards]

        return output_json

    @classmethod
    def from_json(cls, json):
        message = super(KeyboardMessage, cls).from_json(json)

        if 'keyboards' in json:
            keyboards = []
            for keyboard in json['keyboards']:
                kb_type = keyboard['type']
                kb_cls = keyboard_type_mapping.get(kb_type, UnknownKeyboard)
                if kb_cls is not UnknownKeyboard:
                    del keyboard['type']
                keyboards.append(kb_cls.from_json(keyboard))
                keyboard['type'] = kb_type

            if len(keyboards) > 0:
                message.keyboards = keyboards

        return message
