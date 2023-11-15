from js2py import EvalJs
import re


class Decipher:
    def __init__(self, js: str = None, signature: str = None, process=False):
        if process is True:
            self.js = js.replace('\n', '')
            self.signature = signature
            self.main_js = self.get_main_function(js)
            self.var_name,  self.func = self.get_algo_data(self.main_js)
            self.alog_js = self.get_full_function()
        else:
            pass

    def get_main_function(self, js: str):
        main_func = re.search(r"[\{\d\w\(\)\\.\=\"]*?;(..\...\(.\,..?\)\;){3,}.*?}", js)[0]
        return main_func

    def get_algo_data(self, main_js: str):
        main_func = main_js
        variable = re.findall(r'(\w\w)\...', main_func)[0]
        var_regex = r"var "+variable+r"={.+?};"
        func = re.findall(var_regex, self.js)[0]
        var_name = main_func.split('=')[0].split(' ')[-1]
        return [var_name, func]

    def get_full_function(self):
        full_func = self.main_js+self.func+'var output = {0}("{1}");'.format(self.var_name, self.signature)
        return full_func

    def deciphered_signature(self, signature=None, algo_js=None):
        algo_js = algo_js.replace(re.search(r'var output.*?"(.*?)"', algo_js).groups()[0], signature).replace("}var","};var")
        context = EvalJs()
        context.execute(algo_js)
        return context.output